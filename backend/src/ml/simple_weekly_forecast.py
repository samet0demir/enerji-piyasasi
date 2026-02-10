#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basit Haftalik Tahmin - Sadece Prophet v2 Modeli Kullanarak
"""

import pandas as pd
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from prophet.serialize import model_from_json

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/prophet_model_v2.json')

def get_monday_date(offset_weeks=0):
    """Pazartesi tarihini al"""
    today = datetime.now()
    days_since_monday = today.weekday()
    this_monday = today - timedelta(days=days_since_monday)
    target_monday = this_monday + timedelta(weeks=offset_weeks)
    return target_monday.strftime('%Y-%m-%d')

def get_week_dates(monday_str):
    """Pazartesi'den tüm hafta tarihlerini al"""
    monday = datetime.strptime(monday_str, '%Y-%m-%d')
    return [(monday + timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S')
            for i in range(7)
            for hour in range(24)]

def forecast_week(week_monday):
    """Bir hafta için tahmin yap ve DB'ye kaydet"""

    week_sunday = (datetime.strptime(week_monday, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')

    print(f"\n{'='*70}")
    print(f"HAFTALIK TAHMIN: {week_monday} - {week_sunday}")
    print(f"{'='*70}")

    # Model yukle
    print("[1] Model yukleniyor...")
    with open(MODEL_PATH, 'r') as f:
        model = model_from_json(f.read())

    # Haftalik tahmin yap
    print(f"[2] 7 gunluk tahmin yapiliyor...")
    future = model.make_future_dataframe(periods=7*24, freq='H')

    # Feature engineering (v2 model icin)
    future['hour'] = future['ds'].dt.hour
    future['is_sunday'] = future['ds'].dt.dayofweek == 6
    future['is_midday'] = future['hour'].isin([10, 11, 12, 13, 14])
    future['extreme_low_risk'] = (future['is_sunday'] & future['is_midday']).astype(int)

    # Tahmin
    forecast = model.predict(future)

    # Sadece gelecek tarihleri al
    last_date = model.history['ds'].max()
    future_forecast = forecast[forecast['ds'] > last_date].copy()

    # Bu haftanin tahminlerini filtrele
    week_start_dt = datetime.strptime(week_monday, '%Y-%m-%d')
    week_end_dt = datetime.strptime(week_sunday, '%Y-%m-%d') + timedelta(days=1)

    mask = (future_forecast['ds'] >= week_start_dt) & (future_forecast['ds'] < week_end_dt)
    week_forecasts = future_forecast[mask].copy()

    if len(week_forecasts) == 0:
        print(f"[!] Bu hafta icin tahmin uretilmedi!")
        return False

    print(f"[+] {len(week_forecasts)} saatlik tahmin uretildi")
    print(f"    Ortalama: {week_forecasts['yhat'].mean():.2f} TRY")

    # Database'e kaydet
    print(f"[3] Database'e kaydediliyor...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inserted = 0
    for _, row in week_forecasts.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO forecast_history
            (week_start, week_end, forecast_datetime, predicted_price, actual_price,
             absolute_error, percentage_error)
            VALUES (?, ?, ?, ?, NULL, NULL, NULL)
        """, (
            week_monday,
            week_sunday,
            row['ds'].strftime('%Y-%m-%d %H:%M:%S'),
            float(row['yhat'])
        ))
        inserted += 1

    conn.commit()
    conn.close()

    print(f"[+] {inserted} tahmin database'e kaydedildi")

    return True

def update_actuals_and_performance(week_monday):
    """Gercek degerleri cek ve performans hesapla"""

    week_sunday = (datetime.strptime(week_monday, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')

    print(f"\n{'='*70}")
    print(f"PERFORMANS GUNCELLEME: {week_monday} - {week_sunday}")
    print(f"{'='*70}")

    conn = sqlite3.connect(DB_PATH)

    # Gercek degerleri cek
    print("[1] Gercek degerler aliniyor...")
    actual_query = """
        SELECT date, price
        FROM mcp_data
        WHERE date >= ? AND date < datetime(?, '+7 days')
        ORDER BY date
    """
    actuals = pd.read_sql_query(actual_query, conn, params=[week_monday, week_monday])

    if len(actuals) == 0:
        print("[!] Bu hafta icin gercek veri yok!")
        conn.close()
        return False

    print(f"[+] {len(actuals)} gercek deger bulundu")

    # Tahminleri cek
    forecast_query = """
        SELECT forecast_datetime, predicted_price
        FROM forecast_history
        WHERE week_start = ?
        ORDER BY forecast_datetime
    """
    forecasts = pd.read_sql_query(forecast_query, conn, params=[week_monday])

    if len(forecasts) == 0:
        print("[!] Bu hafta icin tahmin yok!")
        conn.close()
        return False

    # Merge
    actuals['forecast_datetime'] = actuals['date']
    merged = forecasts.merge(actuals[['forecast_datetime', 'price']], on='forecast_datetime', how='left')

    # Sadece gercek degeri olan satirlari guncelle
    valid = merged[merged['price'].notna()].copy()

    if len(valid) == 0:
        print("[!] Esleşen veri bulunamadi!")
        conn.close()
        return False

    print(f"[2] {len(valid)} tahmin guncelleniyor...")

    # Hatalari hesapla ve guncelle
    cursor = conn.cursor()
    for _, row in valid.iterrows():
        abs_error = abs(row['predicted_price'] - row['price'])
        pct_error = (abs_error / row['price']) * 100 if row['price'] != 0 else 0

        cursor.execute("""
            UPDATE forecast_history
            SET actual_price = ?,
                absolute_error = ?,
                percentage_error = ?
            WHERE week_start = ? AND forecast_datetime = ?
        """, (
            float(row['price']),
            float(abs_error),
            float(pct_error),
            week_monday,
            row['forecast_datetime']
        ))

    conn.commit()

    # Performans hesapla
    print("[3] Performans hesaplaniyor...")

    mape = (valid['predicted_price'] - valid['price']).abs() / valid['price'] * 100
    mae = (valid['predicted_price'] - valid['price']).abs()
    rmse = ((valid['predicted_price'] - valid['price']) ** 2).mean() ** 0.5

    mape_val = mape.mean()
    mae_val = mae.mean()
    rmse_val = float(rmse)

    print(f"    MAPE: {mape_val:.2f}%")
    print(f"    MAE: {mae_val:.2f} TRY")
    print(f"    RMSE: {rmse_val:.2f} TRY")

    # Weekly performance'a kaydet
    cursor.execute("""
        INSERT OR REPLACE INTO weekly_performance
        (week_start, week_end, mape, mae, rmse, total_predictions)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        week_monday,
        week_sunday,
        float(mape_val),
        float(mae_val),
        float(rmse_val),
        len(valid)
    ))

    conn.commit()
    conn.close()

    print("[+] Performans kaydedildi!")

    return True

def main():
    """Ana fonksiyon"""
    print("\n" + "="*70)
    print("EKSİK HAFTALIK TAHMİNLERİ TELAFI ET (Prophet v2)")
    print("="*70)

    # Eksik haftalar
    weeks = [
        '2026-01-05',  # 5-11 Ocak
        '2026-01-12',  # 12-18 Ocak
        '2026-01-19',  # 19-25 Ocak
        '2026-01-26',  # 26 Ocak - 1 Şubat (bu hafta)
    ]

    for week in weeks:
        # Tahmin yap
        success = forecast_week(week)

        if success:
            # Performans guncelle (gercek veriler varsa)
            update_actuals_and_performance(week)

    print("\n" + "="*70)
    print("TELAFI TAMAMLANDI!")
    print("="*70)

if __name__ == "__main__":
    main()
