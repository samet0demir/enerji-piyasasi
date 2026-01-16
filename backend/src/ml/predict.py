#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ MCP Fiyat Tahmini - Gelecek Tahminleri
============================================

Bu script eğitilmiş Prophet modelini kullanarak
gelecek günler için MCP fiyat tahminleri yapar.
"""

import pandas as pd
import numpy as np
from prophet.serialize import model_from_json
import matplotlib.pyplot as plt
import sqlite3
import os
from datetime import datetime, timedelta

# Model ve database yolu
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/prophet_model.json')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../../models')
DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/energy.db')

def load_model():
    """Eğitilmiş Prophet modelini yükler"""
    print("[*] Model yukleniyor...")

    with open(MODEL_PATH, 'r') as f:
        model = model_from_json(f.read())

    print(f"[+] Model basariyla yuklendi: {MODEL_PATH}")
    return model

def make_forecast(model, days=7):
    """
    Gelecek için tahmin yapar

    Args:
        model: Eğitilmiş Prophet modeli
        days: Kaç gün ileriye tahmin yapılacak

    Returns:
        pd.DataFrame: Tahmin sonuçları
    """
    print(f"\n[*] {days} gun ileriye tahmin yapiliyor...")

    # Gelecek tarihler için dataframe oluştur (saatlik)
    future = model.make_future_dataframe(periods=days*24, freq='H')

    # FEATURE ENGINEERING: Gelecek tarihler için de feature'ları ekle
    print("[*] Feature engineering (gelecek tarihler icin)...")
    future['hour'] = future['ds'].dt.hour
    future['is_weekend'] = (future['ds'].dt.dayofweek >= 5).astype(int)
    future['is_peak_hour'] = future['hour'].isin([8, 9, 10, 18, 19, 20, 21]).astype(int)
    future['is_daytime'] = future['hour'].isin(range(10, 16)).astype(int)
    future['day_of_week'] = future['ds'].dt.dayofweek

    # Tahmin yap
    forecast = model.predict(future)

    # Sadece gelecek tarihleri al
    last_date = model.history['ds'].max()
    future_forecast = forecast[forecast['ds'] > last_date]

    print(f"[+] Tahmin tamamlandi: {len(future_forecast)} saatlik veri")
    print(f"[*] Tarih araligi: {future_forecast['ds'].min()} -> {future_forecast['ds'].max()}")

    return future_forecast

def visualize_forecast(forecast, days=7):
    """
    Tahmin sonuçlarını görselleştirir

    Args:
        forecast: Tahmin dataframe'i
        days: Gösterilecek gün sayısı
    """
    print(f"\n[*] Tahmin grafigi olusturuluyor...")

    # Sadece belirtilen gün sayısı kadar göster
    cutoff_date = forecast['ds'].min() + timedelta(days=days)
    plot_data = forecast[forecast['ds'] <= cutoff_date]

    # Grafik oluştur
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))

    # Üst grafik: Saatlik tahminler
    ax1.plot(plot_data['ds'], plot_data['yhat'], label='Tahmin', color='red', linewidth=2)
    ax1.fill_between(plot_data['ds'],
                      plot_data['yhat_lower'],
                      plot_data['yhat_upper'],
                      alpha=0.3, color='red', label='%95 Guven Araligi')
    ax1.set_xlabel('Tarih')
    ax1.set_ylabel('Fiyat (TRY/MWh)')
    ax1.set_title(f'MCP Fiyat Tahmini - Gelecek {days} Gun (Saatlik)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)

    # Alt grafik: Günlük ortalama
    daily_avg = plot_data.groupby(plot_data['ds'].dt.date).agg({
        'yhat': 'mean',
        'yhat_lower': 'mean',
        'yhat_upper': 'mean'
    }).reset_index()

    ax2.plot(daily_avg['ds'], daily_avg['yhat'], label='Gunluk Ortalama', color='blue', linewidth=2, marker='o')
    ax2.fill_between(range(len(daily_avg)),
                      daily_avg['yhat_lower'],
                      daily_avg['yhat_upper'],
                      alpha=0.3, color='blue', label='%95 Guven Araligi')
    ax2.set_xlabel('Tarih')
    ax2.set_ylabel('Ortalama Fiyat (TRY/MWh)')
    ax2.set_title(f'MCP Fiyat Tahmini - Gelecek {days} Gun (Gunluk Ortalama)')
    ax2.set_xticks(range(len(daily_avg)))
    ax2.set_xticklabels([d.strftime('%Y-%m-%d') for d in daily_avg['ds']], rotation=45)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    # Kaydet
    chart_path = os.path.join(OUTPUT_DIR, f'forecast_{days}days.png')
    plt.savefig(chart_path, dpi=150)
    print(f"[+] Grafik kaydedildi: {chart_path}")

    return daily_avg

def save_forecast_csv(forecast, days=7):
    """
    Tahmin sonuçlarını CSV formatında kaydeder

    Args:
        forecast: Tahmin dataframe'i
        days: Kaydedilecek gün sayısı
    """
    cutoff_date = forecast['ds'].min() + timedelta(days=days)
    export_data = forecast[forecast['ds'] <= cutoff_date][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()

    # Kolon isimlerini Türkçeleştir
    export_data.columns = ['Tarih', 'Tahmin_TRY', 'Alt_Sinir_TRY', 'Ust_Sinir_TRY']

    # CSV olarak kaydet
    csv_path = os.path.join(OUTPUT_DIR, f'forecast_{days}days.csv')
    export_data.to_csv(csv_path, index=False, encoding='utf-8')

    print(f"[+] CSV kaydedildi: {csv_path}")

def save_forecast_to_db(forecast, week_start, week_end):
    """
    Tahminleri forecast_history tablosuna kaydeder

    Args:
        forecast: Tahmin dataframe'i (prophet_component, xgboost_component, lstm_component içerebilir)
        week_start (str): Haftanın başlangıcı (Pazartesi) - Format: 'YYYY-MM-DD'
        week_end (str): Haftanın bitişi (Pazar) - Format: 'YYYY-MM-DD'
    """
    print(f"\n[*] Tahminler database'e kaydediliyor...")
    print(f"   Hafta: {week_start} - {week_end}")

    conn = sqlite3.connect(DB_PATH)

    # Önce bu hafta için eski kayıtları sil (varsa)
    delete_query = "DELETE FROM forecast_history WHERE week_start = ?"
    conn.execute(delete_query, (week_start,))

    # Yeni tahminleri ekle (bileşen değerleri opsiyonel)
    insert_query = """
        INSERT INTO forecast_history (
            week_start, week_end, forecast_datetime, predicted_price,
            prophet_component, xgboost_component, lstm_component
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    inserted = 0
    for _, row in forecast.iterrows():
        # Tarihi string'e çevir (timezone'suz)
        forecast_dt = row['ds'].strftime('%Y-%m-%d %H:%M:%S')
        predicted = float(row['yhat'] if 'yhat' in row else row.get('predicted_price', 0))
        
        # Bileşen değerlerini al (varsa)
        prophet = float(row['prophet_component']) if 'prophet_component' in row else None
        xgboost = float(row['xgboost_component']) if 'xgboost_component' in row else None
        lstm = float(row['lstm_component']) if 'lstm_component' in row else None

        conn.execute(insert_query, (week_start, week_end, forecast_dt, predicted, prophet, xgboost, lstm))
        inserted += 1

    conn.commit()
    conn.close()

    print(f"[+] {inserted} tahmin kaydı database'e eklendi")

def print_summary(forecast, daily_avg):
    """
    Tahmin özetini yazdırır

    Args:
        forecast: Saatlik tahmin dataframe'i
        daily_avg: Günlük ortalama dataframe'i
    """
    print("\n" + "="*60)
    print("Tahmin Ozeti")
    print("="*60)

    print(f"\nSaatlik Tahminler:")
    print(f"  - Minimum fiyat: {forecast['yhat'].min():.2f} TRY")
    print(f"  - Maksimum fiyat: {forecast['yhat'].max():.2f} TRY")
    print(f"  - Ortalama fiyat: {forecast['yhat'].mean():.2f} TRY")

    print(f"\nGunluk Ortalamalar:")
    for idx, row in daily_avg.iterrows():
        print(f"  {row['ds']}: {row['yhat']:.2f} TRY (Alt: {row['yhat_lower']:.2f}, Ust: {row['yhat_upper']:.2f})")

    print("="*60)

def main():
    """Ana tahmin fonksiyonu"""
    print("="*60)
    print("EPIAS MCP Fiyat Tahmini - Gelecek Tahminleri")
    print("="*60)

    # Kullanıcıdan gün sayısı al (varsayılan 7)
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    # 1. Modeli yükle
    model = load_model()

    # 2. Tahmin yap
    forecast = make_forecast(model, days=days)

    # 3. Görselleştir
    daily_avg = visualize_forecast(forecast, days=days)

    # 4. CSV kaydet
    save_forecast_csv(forecast, days=days)

    # 5. Özet yazdır
    print_summary(forecast, daily_avg)

    print("\n[+] Tahmin islemi tamamlandi!")

if __name__ == "__main__":
    main()
