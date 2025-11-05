#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ MCP Fiyat Tahmini - JSON Export
=====================================

Bu script:
1. forecast_history'den bu hafta ve geçen hafta tahminlerini çeker
2. weekly_performance'tan performans trendini çeker
3. Frontend için JSON dosyası oluşturur
"""

import pandas as pd
import sqlite3
import json
import os
from datetime import datetime, timedelta

# Veri tabanı ve output yolu
DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/energy.db')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '../../public/forecasts.json')

def get_current_week_monday():
    """Bugünün ait olduğu haftanın Pazartesi tarihini döndürür"""
    today = datetime.now()
    # Pazartesi = 0, Pazar = 6
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    return monday.strftime('%Y-%m-%d')

def export_forecasts():
    """
    Database'den tahminleri ve performansı çekip JSON'a export eder
    """
    print("\n" + "="*70)
    print("JSON EXPORT - Frontend için veri hazırlama")
    print("="*70)

    conn = sqlite3.connect(DB_PATH)

    # Bu haftanın Pazartesi'si
    this_week_monday = get_current_week_monday()
    this_week_sunday = (datetime.strptime(this_week_monday, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')

    # Geçen haftanın Pazartesi'si
    last_week_monday = (datetime.strptime(this_week_monday, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
    last_week_sunday = (datetime.strptime(last_week_monday, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')

    print(f"\n[*] Bu hafta: {this_week_monday} - {this_week_sunday}")
    print(f"[*] Geçen hafta: {last_week_monday} - {last_week_sunday}")

    # 1. Bu hafta tahminleri
    print(f"\n[*] Bu hafta tahminleri yükleniyor...")
    current_week_query = """
        SELECT forecast_datetime, predicted_price, actual_price, absolute_error
        FROM forecast_history
        WHERE week_start = ?
        ORDER BY forecast_datetime
    """
    current_week = pd.read_sql_query(current_week_query, conn, params=[this_week_monday])

    current_forecasts = []
    if len(current_week) > 0:
        for _, row in current_week.iterrows():
            current_forecasts.append({
                'datetime': row['forecast_datetime'],
                'predicted': round(row['predicted_price'], 2),
                'actual': round(row['actual_price'], 2) if pd.notna(row['actual_price']) else None
            })
        print(f"[+] {len(current_forecasts)} tahmin bulundu")
    else:
        print(f"[!] Bu hafta için tahmin bulunamadı!")

    # 2. Geçen hafta performansı
    print(f"\n[*] Geçen hafta performansı yükleniyor...")
    last_week_perf_query = """
        SELECT mape, mae, rmse, total_predictions
        FROM weekly_performance
        WHERE week_start = ?
    """
    last_week_perf = pd.read_sql_query(last_week_perf_query, conn, params=[last_week_monday])

    last_week_performance = None
    if len(last_week_perf) > 0:
        row = last_week_perf.iloc[0]
        last_week_performance = {
            'week': f"{last_week_monday} - {last_week_sunday}",
            'mape': round(row['mape'], 2),
            'mae': round(row['mae'], 2),
            'rmse': round(row['rmse'], 2),
            'total_predictions': int(row['total_predictions'])
        }
        print(f"[+] Performans: MAPE {row['mape']:.2f}%, MAE {row['mae']:.2f} TRY")
    else:
        print(f"[!] Geçen hafta performansı bulunamadı")

    # 3. Geçen hafta karşılaştırma (tahmin vs gerçek)
    print(f"\n[*] Geçen hafta karşılaştırması yükleniyor...")
    last_week_comparison_query = """
        SELECT forecast_datetime, predicted_price, actual_price, absolute_error, percentage_error
        FROM forecast_history
        WHERE week_start = ? AND actual_price IS NOT NULL
        ORDER BY forecast_datetime
    """
    last_week_comp = pd.read_sql_query(last_week_comparison_query, conn, params=[last_week_monday])

    last_week_comparison = []
    if len(last_week_comp) > 0:
        for _, row in last_week_comp.iterrows():
            last_week_comparison.append({
                'datetime': row['forecast_datetime'],
                'predicted': round(row['predicted_price'], 2),
                'actual': round(row['actual_price'], 2),
                'error': round(row['absolute_error'], 2),
                'error_percent': round(row['percentage_error'], 2)
            })
        print(f"[+] {len(last_week_comparison)} karşılaştırma kaydı bulundu")
    else:
        print(f"[!] Geçen hafta karşılaştırması bulunamadı")

    # 4. Haftalık performans trendi (son 8 hafta)
    print(f"\n[*] Haftalık performans trendi yükleniyor...")
    trend_query = """
        SELECT week_start, week_end, mape, mae, rmse
        FROM weekly_performance
        ORDER BY week_start DESC
        LIMIT 8
    """
    trend = pd.read_sql_query(trend_query, conn)

    historical_trend = []
    if len(trend) > 0:
        for _, row in trend.iterrows():
            historical_trend.append({
                'week': f"{row['week_start']} - {row['week_end']}",
                'week_start': row['week_start'],
                'week_end': row['week_end'],
                'mape': round(row['mape'], 2),
                'mae': round(row['mae'], 2),
                'rmse': round(row['rmse'], 2)
            })
        print(f"[+] {len(historical_trend)} haftalık performans kaydı bulundu")
    else:
        print(f"[!] Performans trendi bulunamadı")

    conn.close()

    # 5. JSON oluştur
    print(f"\n[*] JSON dosyası oluşturuluyor...")
    output_data = {
        'generated_at': datetime.now().isoformat(),
        'current_week': {
            'start': this_week_monday,
            'end': this_week_sunday,
            'forecasts': current_forecasts
        },
        'last_week_performance': last_week_performance,
        'last_week_comparison': last_week_comparison,
        'historical_trend': historical_trend
    }

    # public klasörünü oluştur
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # JSON'u kaydet (backend/public)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"[+] JSON dosyası kaydedildi: {OUTPUT_PATH}")
    print(f"   Dosya boyutu: {os.path.getsize(OUTPUT_PATH) / 1024:.2f} KB")

    # Frontend'e de kopyala
    frontend_path = os.path.join(os.path.dirname(__file__), '../../../frontend/public/forecasts.json')
    os.makedirs(os.path.dirname(frontend_path), exist_ok=True)

    with open(frontend_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"[+] Frontend JSON kopyalandı: {frontend_path}")
    print("="*70)

    return output_data

def main():
    """Ana fonksiyon"""
    try:
        data = export_forecasts()
        print("\n[+] JSON export başarılı!")
        return data
    except Exception as e:
        print(f"\n[!] HATA: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()
