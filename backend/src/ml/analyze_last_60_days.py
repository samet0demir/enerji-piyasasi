#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Son 60 günün detaylı analizi - 0 TRY fiyatların etkisi
"""

import pandas as pd
import numpy as np
from prophet.serialize import model_from_json
import sqlite3
import os
import sys

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/prophet_model.json')

def main():
    print("="*60)
    print("Son 60 Gun Detayli Analiz - 0 TRY Fiyatlarin Etkisi")
    print("="*60)

    # Veri yükle
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT date as ds, price as y
        FROM mcp_data
        WHERE date >= '2025-08-17'
        ORDER BY date
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    df['ds'] = pd.to_datetime(df['ds']).dt.tz_localize(None)

    print(f"\n[*] Toplam kayit: {len(df)}")
    print(f"[*] Tarih araligi: {df['ds'].min()} -> {df['ds'].max()}")

    # Model yükle
    with open(MODEL_PATH, 'r') as f:
        model = model_from_json(f.read())

    # Tahmin
    forecast = model.predict(df[['ds']])

    y_true = df['y'].values
    y_pred = forecast['yhat'].values

    # 0 ve 0 olmayan değerleri ayır
    zero_mask = y_true == 0
    nonzero_mask = y_true != 0

    zero_count = zero_mask.sum()
    nonzero_count = nonzero_mask.sum()

    print(f"\n[*] Fiyat dagilimi:")
    print(f"    0 TRY fiyatlar: {zero_count} adet ({zero_count/len(df)*100:.2f}%)")
    print(f"    Normal fiyatlar: {nonzero_count} adet ({nonzero_count/len(df)*100:.2f}%)")

    # 0 TRY değerler için analiz
    if zero_count > 0:
        print(f"\n{'='*60}")
        print("0 TRY FIYATLAR ANALIZI")
        print(f"{'='*60}")
        zero_data = df[zero_mask].copy()
        zero_preds = y_pred[zero_mask]

        print(f"\nTarihler:")
        for idx, (_, row) in enumerate(zero_data.iterrows()):
            ds = row['ds']
            pred = zero_preds[idx]
            print(f"  {ds.strftime('%Y-%m-%d %H:%M')} ({ds.strftime('%A'):9s}) -> Tahmin: {pred:.2f} TRY")

        print(f"\nTahmin istatistikleri (0 TRY gercek degerler icin):")
        print(f"  Ortalama tahmin: {zero_preds.mean():.2f} TRY")
        print(f"  Min tahmin: {zero_preds.min():.2f} TRY")
        print(f"  Max tahmin: {zero_preds.max():.2f} TRY")

    # Normal değerler için performans
    if nonzero_count > 0:
        print(f"\n{'='*60}")
        print("NORMAL FIYATLAR PERFORMANSI (0 TRY haric)")
        print(f"{'='*60}")

        y_true_nonzero = y_true[nonzero_mask]
        y_pred_nonzero = y_pred[nonzero_mask]

        mae = np.mean(np.abs(y_true_nonzero - y_pred_nonzero))
        rmse = np.sqrt(np.mean((y_true_nonzero - y_pred_nonzero)**2))
        mape = np.mean(np.abs((y_true_nonzero - y_pred_nonzero) / y_true_nonzero)) * 100

        print(f"\nMetrikler:")
        print(f"  MAE:  {mae:.2f} TRY")
        print(f"  RMSE: {rmse:.2f} TRY")
        print(f"  MAPE: {mape:.2f}%")

        print(f"\nGercek deger istatistikleri:")
        print(f"  Ortalama: {y_true_nonzero.mean():.2f} TRY")
        print(f"  Min: {y_true_nonzero.min():.2f} TRY")
        print(f"  Max: {y_true_nonzero.max():.2f} TRY")

    # Tüm veri (0 dahil)
    print(f"\n{'='*60}")
    print("TUM VERI PERFORMANSI (0 TRY dahil)")
    print(f"{'='*60}")

    mae_all = np.mean(np.abs(y_true - y_pred))
    rmse_all = np.sqrt(np.mean((y_true - y_pred)**2))

    print(f"\nMetrikler:")
    print(f"  MAE:  {mae_all:.2f} TRY")
    print(f"  RMSE: {rmse_all:.2f} TRY")
    print(f"  MAPE: Hesaplanamaz (0 degerler var)")

    # Sonuç
    print(f"\n{'='*60}")
    print("SONUC")
    print(f"{'='*60}")

    if zero_count > 0:
        avg_zero_pred = y_pred[zero_mask].mean()
        if avg_zero_pred > 1000:
            print(f"\n!!! PROBLEM: Model 0 TRY fiyatlari tahmin edemiyor!")
            print(f"    Gercek: 0 TRY")
            print(f"    Tahmin: {avg_zero_pred:.2f} TRY (Ortalama)")
            print(f"\n    NEDEN: Model bu kadar dusuk fiyatlari ogrenmemis.")
            print(f"    COZUM: Daha fazla 0 TRY ornek eklemek veya")
            print(f"           extreme low price regressor eklemek gerekli.")
        else:
            print(f"\n✅ Model dusuk fiyatlari makul tahmin ediyor.")

    if nonzero_count > 0 and mape < 30:
        print(f"\n✅ Normal fiyatlar icin model iyi calisiyor (MAPE: {mape:.2f}%)")
    elif nonzero_count > 0:
        print(f"\n⚠️  Normal fiyatlar icin model orta performans (MAPE: {mape:.2f}%)")

    print("="*60)

if __name__ == "__main__":
    main()
