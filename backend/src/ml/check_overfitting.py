#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prophet modelinde overfitting kontrolü
"""

import pandas as pd
import numpy as np
from prophet import Prophet
from prophet.serialize import model_from_json
import sqlite3
from datetime import timedelta
import os

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/prophet_model.json')

def load_data():
    """Veri tabanından veri yükle"""
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT date as ds, price as y FROM mcp_data ORDER BY date"
    df = pd.read_sql_query(query, conn)
    conn.close()
    df['ds'] = pd.to_datetime(df['ds']).dt.tz_localize(None)
    return df

def create_train_test_splits(df):
    """Farklı zaman dilimlerinde train/test split'leri oluştur"""
    splits = []

    # Split 1: İlk 60 gün test (2023-10-16 - 2023-12-15)
    split1_date = df['ds'].min() + timedelta(days=60)
    splits.append({
        'name': 'Baslangic 60 gun',
        'train': df[df['ds'] > split1_date],
        'test': df[df['ds'] <= split1_date]
    })

    # Split 2: Orta 60 gün test (yaklaşık 1 yıl sonra)
    split2_start = df['ds'].min() + timedelta(days=365)
    split2_end = split2_start + timedelta(days=60)
    splits.append({
        'name': 'Ortada 60 gun (1 yil sonra)',
        'train': df[(df['ds'] < split2_start) | (df['ds'] > split2_end)],
        'test': df[(df['ds'] >= split2_start) & (df['ds'] <= split2_end)]
    })

    # Split 3: Son 60 gün test (mevcut model)
    split3_date = df['ds'].max() - timedelta(days=60)
    splits.append({
        'name': 'Son 60 gun',
        'train': df[df['ds'] <= split3_date],
        'test': df[df['ds'] > split3_date]
    })

    return splits

def evaluate_split(train, test, split_name):
    """Bir split için model eğit ve değerlendir"""
    print(f"\n{'='*60}")
    print(f"Split: {split_name}")
    print(f"{'='*60}")
    print(f"Train: {len(train)} kayit ({train['ds'].min()} -> {train['ds'].max()})")
    print(f"Test:  {len(test)} kayit ({test['ds'].min()} -> {test['ds'].max()})")

    # Model eğit
    model = Prophet(
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True,
        changepoint_prior_scale=0.05,
        holidays_prior_scale=10.0,
        seasonality_prior_scale=10.0,
    )
    model.add_country_holidays('TR')
    model.fit(train)

    # Tahmin
    forecast = model.predict(test[['ds']])

    # Metrikler
    y_true = test['y'].values
    y_pred = forecast['yhat'].values

    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))

    mask = y_true != 0
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.sum() > 0 else 0

    print(f"\nMetrikler:")
    print(f"  MAE:  {mae:.2f} TRY")
    print(f"  RMSE: {rmse:.2f} TRY")
    print(f"  MAPE: {mape:.2f}%")

    return mae, rmse, mape

def main():
    print("="*60)
    print("Overfitting Kontrolu - Farkli Zaman Dilimlerinde Test")
    print("="*60)

    # Veri yükle
    df = load_data()

    # Farklı split'ler oluştur
    splits = create_train_test_splits(df)

    # Her split'i değerlendir
    results = []
    for split in splits:
        mae, rmse, mape = evaluate_split(split['train'], split['test'], split['name'])
        results.append({
            'split': split['name'],
            'mae': mae,
            'rmse': rmse,
            'mape': mape
        })

    # Sonuçları karşılaştır
    print(f"\n{'='*60}")
    print("SONUC: Overfitting Analizi")
    print(f"{'='*60}")

    maes = [r['mape'] for r in results]
    avg_mape = np.mean(maes)
    std_mape = np.std(maes)

    print(f"\nMAPE Dagilimi:")
    for r in results:
        print(f"  {r['split']:30s}: {r['mape']:6.2f}%")

    print(f"\nIstatistikler:")
    print(f"  Ortalama MAPE: {avg_mape:.2f}%")
    print(f"  Standart Sapma: {std_mape:.2f}%")
    print(f"  Varyans Katsayisi: {(std_mape/avg_mape)*100:.2f}%")

    print(f"\nDegerlendirme:")
    if std_mape / avg_mape < 0.15:  # %15'ten az varyasyon
        print("  ✅ OVERFITTING YOK - Model tutarli performans gosteriyor")
    elif std_mape / avg_mape < 0.30:
        print("  ⚠️  HAFIF OVERFITTING - Kabul edilebilir seviyede")
    else:
        print("  ❌ CIDDI OVERFITTING - Model genelleme yapamıyor")

    print("="*60)

if __name__ == "__main__":
    main()
