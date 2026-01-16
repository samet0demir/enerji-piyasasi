#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Model Bileşenleri Backfill Script
=================================

Mevcut forecast_history kayıtlarına model bileşen değerlerini ekler.
Bu script bir defaya mahsus çalıştırılır.
"""

import sys
import os
from datetime import datetime, timedelta
import sqlite3

# Path ayarları
script_dir = os.path.dirname(os.path.abspath(__file__))
ml_dir = os.path.join(script_dir, '../ml')
sys.path.append(ml_dir)

# ML modülleri
from ensemble import EnsembleModel
from features import load_combined_data, engineer_features

# Veritabanı yolu
DB_PATH = os.path.join(script_dir, '../../data/energy.db')

def get_weeks_without_components():
    """Model bileşen verisi olmayan haftaları döndürür"""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT DISTINCT week_start, week_end
        FROM forecast_history
        WHERE prophet_component IS NULL
        ORDER BY week_start DESC
    """
    weeks = conn.execute(query).fetchall()
    conn.close()
    return weeks

def update_week_components(week_start, week_end, ensemble, df):
    """Belirli bir hafta için model bileşen değerlerini hesaplar ve günceller"""
    print(f"\n[*] {week_start} haftası için bileşenler hesaplanıyor...")
    
    # Hafta için tahmin tarihlerini al
    conn = sqlite3.connect(DB_PATH)
    forecast_query = """
        SELECT id, forecast_datetime
        FROM forecast_history
        WHERE week_start = ?
        ORDER BY forecast_datetime ASC
    """
    forecasts = conn.execute(forecast_query, (week_start,)).fetchall()
    
    if len(forecasts) == 0:
        print(f"   [!] Bu hafta için tahmin bulunamadı")
        conn.close()
        return 0
    
    # Ensemble model ile tüm veri üzerinde tahmin yap
    try:
        predictions = ensemble.predict(df)
        prophet_all = predictions['prophet_pred']
        xgboost_all = predictions['xgboost_pred']
        lstm_all = predictions['lstm_pred']
    except Exception as e:
        print(f"   [!] Tahmin hatası: {e}")
        conn.close()
        return 0
    
    # Her forecast için eşleşen bileşen değerlerini bul
    updated = 0
    update_query = """
        UPDATE forecast_history
        SET prophet_component = ?, xgboost_component = ?, lstm_component = ?
        WHERE id = ?
    """
    
    for forecast_id, forecast_dt in forecasts:
        # forecast_datetime'ı datetime'a çevir
        dt = datetime.strptime(forecast_dt, '%Y-%m-%d %H:%M:%S')
        
        # df'de bu tarihi bul - positional index kullan
        mask = df['ds'] == dt
        if mask.sum() > 0:
            # Pozisyonel indeks bul (iloc için)
            pos_idx = mask.values.argmax()
            
            try:
                prophet_val = float(prophet_all[pos_idx])
                xgboost_val = float(xgboost_all[pos_idx])
                lstm_val = float(lstm_all[pos_idx])
                
                conn.execute(update_query, (prophet_val, xgboost_val, lstm_val, forecast_id))
                updated += 1
            except (IndexError, KeyError) as e:
                # Bu tarih için veri yoksa atla
                pass
    
    conn.commit()
    conn.close()
    
    print(f"   [+] {updated} kayıt güncellendi")
    return updated

def main():
    print("=" * 60)
    print("MODEL BİLEŞENLERİ BACKFILL")
    print("=" * 60)
    
    # 1. Bileşen verisi olmayan haftaları bul
    weeks = get_weeks_without_components()
    
    if len(weeks) == 0:
        print("[+] Tüm haftalarda bileşen verileri mevcut!")
        return
    
    print(f"[*] {len(weeks)} hafta için bileşen verileri eksik")
    
    # 2. Veri ve model yükle
    print("\n[*] Veri yükleniyor...")
    df = load_combined_data()
    df = engineer_features(df)
    print(f"   [+] {len(df)} satır veri yüklendi")
    
    print("\n[*] Ensemble model yükleniyor...")
    ensemble = EnsembleModel()
    ensemble.load_models()
    
    # 3. Her hafta için bileşen değerlerini hesapla
    total_updated = 0
    for week_start, week_end in weeks:
        updated = update_week_components(week_start, week_end, ensemble, df)
        total_updated += updated
    
    print("\n" + "=" * 60)
    print(f"[+] TAMAMLANDI: {total_updated} kayıt güncellendi")
    print("=" * 60)

if __name__ == "__main__":
    main()
