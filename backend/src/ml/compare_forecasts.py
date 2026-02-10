#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ MCP Fiyat Tahmini - Tahmin vs Gerçek Karşılaştırma
=======================================================

Bu script:
1. forecast_history tablosundan belirli bir hafta için tahminleri çeker
2. mcp_data tablosundan aynı hafta için gerçek değerleri çeker
3. Performans metriklerini hesaplar (MAPE, MAE, RMSE)
4. forecast_history'yi günceller (actual_price, errors)
5. weekly_performance tablosuna sonuçları kaydeder
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime, timedelta
import sys

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH

def compare_week(week_start, week_end):
    """
    Belirli bir hafta için tahmin vs gerçek karşılaştırması yapar

    Args:
        week_start (str): Haftanın başlangıcı (Pazartesi) - Format: 'YYYY-MM-DD'
        week_end (str): Haftanın bitişi (Pazar) - Format: 'YYYY-MM-DD'

    Returns:
        dict: Performans metrikleri (mape, mae, rmse, total_predictions)
    """
    print("\n" + "="*70)
    print(f"HAFTALIK KARŞILAŞTIRMA: {week_start} - {week_end}")
    print("="*70)

    conn = sqlite3.connect(DB_PATH)

    # 1. Tahminleri çek
    print(f"\n[*] {week_start} - {week_end} için tahminler yükleniyor...")
    forecast_query = """
        SELECT forecast_datetime, predicted_price
        FROM forecast_history
        WHERE week_start = ?
        ORDER BY forecast_datetime
    """
    forecasts = pd.read_sql_query(forecast_query, conn, params=[week_start])

    if len(forecasts) == 0:
        print(f"[!] UYARI: {week_start} için tahmin bulunamadı!")
        conn.close()
        return None

    print(f"[+] {len(forecasts)} tahmin kaydı bulundu")

    # 2. Gerçek değerleri çek
    print(f"[*] Gerçek değerler yükleniyor...")

    # week_end'i dahil et (Pazar günü dahil)
    # Bug fix: Use < next_day instead of <= week_end to handle ISO datetime strings properly
    next_day = (datetime.strptime(week_end, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    actual_query = """
        SELECT date, price
        FROM mcp_data
        WHERE date >= ? AND date < ?
        ORDER BY date
    """
    actuals = pd.read_sql_query(actual_query, conn, params=[week_start, next_day])

    if len(actuals) == 0:
        print(f"[!] UYARI: {week_start} - {week_end} için gerçek veri bulunamadı!")
        conn.close()
        return None

    print(f"[+] {len(actuals)} gerçek kayıt bulundu")

    # 3. Tahmin ve gerçek verileri birleştir
    # forecast_datetime ve date'i normalize et
    forecasts['ds'] = pd.to_datetime(forecasts['forecast_datetime']).dt.tz_localize(None)
    actuals['ds'] = pd.to_datetime(actuals['date']).dt.tz_localize(None)

    # Merge
    comparison = pd.merge(
        forecasts,
        actuals,
        left_on='ds',
        right_on='ds',
        how='inner'
    )

    if len(comparison) == 0:
        print("[!] HATA: Tahmin ve gerçek veriler eşleştirilemedi!")
        conn.close()
        return None

    print(f"[+] {len(comparison)} eşleşme bulundu")

    # 4. Hata metriklerini hesapla
    y_true = comparison['price'].values
    y_pred = comparison['predicted_price'].values

    # Mutlak hatalar
    absolute_errors = np.abs(y_true - y_pred)
    percentage_errors = (absolute_errors / y_true) * 100

    # MAE (Mean Absolute Error)
    mae = np.mean(absolute_errors)

    # RMSE (Root Mean Squared Error)
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))

    # MAPE (Mean Absolute Percentage Error) - sıfır olmayan değerler için
    mask = y_true > 100  # 100 TRY'den büyük fiyatlar (0 TRY'yi filtrele)
    mape = np.mean(percentage_errors[mask]) if mask.sum() > 0 else 0

    print(f"\n[*] PERFORMANS METRİKLERİ:")
    print(f"   MAE  (Ortalama Mutlak Hata)  : {mae:.2f} TRY")
    print(f"   RMSE (Kök Ortalama Kare Hata): {rmse:.2f} TRY")
    print(f"   MAPE (Ortalama Yüzde Hata)   : {mape:.2f}%")
    print(f"   Toplam Tahmin                : {len(comparison)}")

    # 5. forecast_history'yi güncelle (actual_price, errors)
    print(f"\n[*] forecast_history tablosu güncelleniyor...")

    for idx, row in comparison.iterrows():
        update_query = """
            UPDATE forecast_history
            SET actual_price = ?,
                absolute_error = ?,
                percentage_error = ?
            WHERE week_start = ? AND forecast_datetime = ?
        """
        conn.execute(update_query, (
            row['price'],
            absolute_errors[idx],
            percentage_errors[idx],
            week_start,
            row['forecast_datetime']
        ))

    conn.commit()
    print(f"[+] {len(comparison)} kayıt güncellendi")

    # 6. weekly_performance tablosuna kaydet
    print(f"[*] weekly_performance tablosuna kaydediliyor...")

    # Önce bu hafta için kayıt var mı kontrol et
    check_query = "SELECT COUNT(*) as count FROM weekly_performance WHERE week_start = ?"
    result = conn.execute(check_query, (week_start,)).fetchone()

    if result[0] > 0:
        # Güncelle
        update_query = """
            UPDATE weekly_performance
            SET mape = ?, mae = ?, rmse = ?, total_predictions = ?
            WHERE week_start = ?
        """
        conn.execute(update_query, (mape, mae, rmse, len(comparison), week_start))
    else:
        # Yeni kayıt ekle
        insert_query = """
            INSERT INTO weekly_performance (week_start, week_end, mape, mae, rmse, total_predictions)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        conn.execute(insert_query, (week_start, week_end, mape, mae, rmse, len(comparison)))

    conn.commit()
    conn.close()

    print(f"[+] Performans metrikleri kaydedildi")
    print("="*70)

    return {
        'mape': mape,
        'mae': mae,
        'rmse': rmse,
        'total_predictions': len(comparison)
    }

def main():
    """Test için örnek kullanım"""
    import sys

    if len(sys.argv) < 3:
        print("Kullanım: python compare_forecasts.py <week_start> <week_end>")
        print("Örnek: python compare_forecasts.py 2025-10-20 2025-10-26")
        sys.exit(1)

    week_start = sys.argv[1]
    week_end = sys.argv[2]

    result = compare_week(week_start, week_end)

    if result:
        print(f"\n[+] Karşılaştırma tamamlandı!")
        print(f"   MAPE: {result['mape']:.2f}%")
        print(f"   MAE: {result['mae']:.2f} TRY")
    else:
        print("\n[!] Karşılaştırma yapılamadı!")

if __name__ == "__main__":
    main()
