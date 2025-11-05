#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Haftalık Tahmin vs Gerçek Karşılaştırması
"""

import sqlite3
import pandas as pd
import numpy as np
import os

# Database
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, '../../data/energy.db')
conn = sqlite3.connect(db_path)

def compare_week(week_start, week_end, week_name):
    """Bir haftanın tahmin vs gerçek karşılaştırması"""

    print("\n" + "="*80)
    print(f"{week_name}: {week_start} - {week_end}")
    print("="*80)

    # Tahminleri çek
    df_forecast = pd.read_sql_query(f"""
    SELECT
        forecast_datetime as tarih,
        predicted_price as tahmin
    FROM forecast_history
    WHERE week_start = '{week_start}'
    ORDER BY forecast_datetime
    """, conn)

    # Gerçek verileri çek
    df_actual = pd.read_sql_query(f"""
    SELECT
        datetime(date) as tarih,
        price as gercek
    FROM mcp_data
    WHERE date >= '{week_start}' AND date < datetime('{week_end}', '+1 day')
    ORDER BY date
    """, conn)

    if len(df_forecast) == 0:
        print("[X] Tahmin yok!")
        return

    if len(df_actual) == 0:
        print("[!] Gercek veri henuz yok (gelecek hafta)")
        return

    # Birleştir
    df_forecast['tarih'] = pd.to_datetime(df_forecast['tarih'])
    df_actual['tarih'] = pd.to_datetime(df_actual['tarih'])

    df_merged = pd.merge(df_forecast, df_actual, on='tarih', how='inner')

    if len(df_merged) == 0:
        print("[!] Eslesen veri yok!")
        return

    # Metrikler hesapla
    y_true = df_merged['gercek'].values
    y_pred = df_merged['tahmin'].values

    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))

    # MAPE (500+ TRY için)
    mask = y_true >= 500
    if mask.sum() > 0:
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    else:
        mape = float('inf')

    # Günlük karşılaştırma
    df_merged['gun'] = df_merged['tarih'].dt.date
    daily_comparison = df_merged.groupby('gun').agg({
        'gercek': 'mean',
        'tahmin': 'mean'
    }).round(2)
    daily_comparison['fark'] = (daily_comparison['tahmin'] - daily_comparison['gercek']).round(2)
    daily_comparison['fark_yuzde'] = ((daily_comparison['fark'] / daily_comparison['gercek']) * 100).round(2)

    print(f"\nPerformans Metrikleri:")
    print(f"  MAE (Ortalama Mutlak Hata): {mae:.2f} TRY")
    print(f"  RMSE (Kok Ortalama Kare Hata): {rmse:.2f} TRY")
    print(f"  MAPE (500+ TRY icin): {mape:.2f}%")
    print(f"  Karsilastirilan kayit: {len(df_merged)} saat")

    print(f"\nGunluk Ortalama Karsilastirma:")
    print(daily_comparison.to_string())

    return {
        'week': week_name,
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'records': len(df_merged)
    }

# Haftaları karşılaştır
print("="*80)
print("HAFTALIK TAHMİN vs GERÇEK KARŞILAŞTIRMASI")
print("="*80)

results = []

# 1. Hafta
result1 = compare_week('2025-10-20', '2025-10-26', '1. HAFTA')
if result1:
    results.append(result1)

# 2. Hafta
result2 = compare_week('2025-10-27', '2025-11-02', '2. HAFTA')
if result2:
    results.append(result2)

# 3. Hafta
result3 = compare_week('2025-11-03', '2025-11-09', '3. HAFTA')
if result3:
    results.append(result3)

# Özet
if results:
    print("\n\n" + "="*80)
    print("GENEL ÖZET")
    print("="*80)
    df_summary = pd.DataFrame(results)
    print(df_summary.to_string(index=False))

    print(f"\n[*] Ortalama MAE: {df_summary['mae'].mean():.2f} TRY")
    print(f"[*] Ortalama RMSE: {df_summary['rmse'].mean():.2f} TRY")
    print(f"[*] Ortalama MAPE: {df_summary['mape'].mean():.2f}%")
    print("="*80)

conn.close()
