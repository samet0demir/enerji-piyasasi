#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Model karsilastirmasi: v1 (original) vs v2 (improved)
"""

import pandas as pd
import numpy as np
from prophet.serialize import model_from_json
import sqlite3
from datetime import timedelta
import os
import sys

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH
MODEL_V1 = os.path.join(os.path.dirname(__file__), '../../models/prophet_model.json')
MODEL_V2 = os.path.join(os.path.dirname(__file__), '../../models/prophet_model_v2.json')

def load_data():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT date as ds, price as y FROM mcp_data ORDER BY date"
    df = pd.read_sql_query(query, conn)
    conn.close()
    df['ds'] = pd.to_datetime(df['ds']).dt.tz_localize(None)
    return df

def add_regressors(df):
    """v2 model icin regressorlari ekle"""
    df = df.copy()
    df['is_sunday'] = df['ds'].dt.dayofweek == 6
    df['is_midday'] = df['ds'].dt.hour.isin([10, 11, 12, 13, 14])
    df['extreme_low_risk'] = (df['is_sunday'] & df['is_midday']).astype(int)
    return df

def evaluate_model(model, test_data, model_name, use_regressor=False):
    """Model performansini olc"""
    print(f"\n{'='*70}")
    print(f"Model: {model_name}")
    print(f"{'='*70}")

    if use_regressor:
        test_data = add_regressors(test_data)
        forecast = model.predict(test_data[['ds', 'extreme_low_risk']])
    else:
        forecast = model.predict(test_data[['ds']])

    y_true = test_data['y'].values
    y_pred = forecast['yhat'].values

    # Tum veri
    mae_all = np.mean(np.abs(y_true - y_pred))
    rmse_all = np.sqrt(np.mean((y_true - y_pred)**2))

    # Normal fiyatlar (>=100 TRY)
    normal_mask = y_true >= 100
    y_true_normal = y_true[normal_mask]
    y_pred_normal = y_pred[normal_mask]

    mae_normal = np.mean(np.abs(y_true_normal - y_pred_normal))
    rmse_normal = np.sqrt(np.mean((y_true_normal - y_pred_normal)**2))
    mape_normal = np.mean(np.abs((y_true_normal - y_pred_normal) / y_true_normal)) * 100

    # Ekstrem dusuk fiyatlar (0-100 TRY)
    extreme_mask = y_true < 100
    if extreme_mask.sum() > 0:
        y_true_extreme = y_true[extreme_mask]
        y_pred_extreme = y_pred[extreme_mask]
        mae_extreme = np.mean(np.abs(y_true_extreme - y_pred_extreme))
    else:
        mae_extreme = 0

    print(f"\nTum Veri:")
    print(f"  MAE:  {mae_all:.2f} TRY")
    print(f"  RMSE: {rmse_all:.2f} TRY")

    print(f"\nNormal Fiyatlar (>= 100 TRY): {normal_mask.sum()} kayit")
    print(f"  MAE:  {mae_normal:.2f} TRY")
    print(f"  RMSE: {rmse_normal:.2f} TRY")
    print(f"  MAPE: {mape_normal:.2f}%")

    print(f"\nEkstrem Dusuk (<100 TRY): {extreme_mask.sum()} kayit")
    print(f"  MAE:  {mae_extreme:.2f} TRY")

    return {
        'model': model_name,
        'mae_all': mae_all,
        'rmse_all': rmse_all,
        'mae_normal': mae_normal,
        'rmse_normal': rmse_normal,
        'mape_normal': mape_normal,
        'mae_extreme': mae_extreme,
        'extreme_count': extreme_mask.sum()
    }

def main():
    print("="*70)
    print("MODEL KARSILASTIRMASI: v1 (Original) vs v2 (Improved)")
    print("="*70)

    # Veri yukle
    df = load_data()

    # Son 60 gun test
    test_start = df['ds'].max() - timedelta(days=60)
    test_data = df[df['ds'] > test_start].copy()

    print(f"\n[*] Test verisi: {len(test_data)} kayit")
    print(f"[*] Tarih: {test_data['ds'].min()} -> {test_data['ds'].max()}")

    # Model v1 yukle
    print(f"\n[*] Model v1 yukleniyor...")
    with open(MODEL_V1, 'r') as f:
        model_v1 = model_from_json(f.read())

    # Model v2 yukle
    print(f"[*] Model v2 yukleniyor...")
    with open(MODEL_V2, 'r') as f:
        model_v2 = model_from_json(f.read())

    # Degerlendirme
    results_v1 = evaluate_model(model_v1, test_data, "v1 (Original)", use_regressor=False)
    results_v2 = evaluate_model(model_v2, test_data, "v2 (Improved)", use_regressor=True)

    # Karsilastirma
    print(f"\n{'='*70}")
    print("KARSILASTIRMA OZETI")
    print(f"{'='*70}")

    print(f"\n{'Metrik':30s} {'v1 (Original)':15s} {'v2 (Improved)':15s} {'Iyilesme':15s}")
    print("-"*70)

    metrics = [
        ('MAE (Tum Veri)', 'mae_all', 'TRY'),
        ('RMSE (Tum Veri)', 'rmse_all', 'TRY'),
        ('MAE (Normal)', 'mae_normal', 'TRY'),
        ('RMSE (Normal)', 'rmse_normal', 'TRY'),
        ('MAPE (Normal)', 'mape_normal', '%'),
        ('MAE (Ekstrem)', 'mae_extreme', 'TRY'),
    ]

    for metric_name, metric_key, unit in metrics:
        v1_val = results_v1[metric_key]
        v2_val = results_v2[metric_key]
        improvement = ((v1_val - v2_val) / v1_val * 100) if v1_val > 0 else 0

        v1_str = f"{v1_val:.2f} {unit}"
        v2_str = f"{v2_val:.2f} {unit}"

        if improvement > 0:
            imp_str = f"-{improvement:.1f}% "
        elif improvement < 0:
            imp_str = f"+{-improvement:.1f}% "
        else:
            imp_str = "Aynı"

        print(f"{metric_name:30s} {v1_str:15s} {v2_str:15s} {imp_str:15s}")

    # Sonuc
    print(f"\n{'='*70}")
    print("SONUC")
    print(f"{'='*70}")

    overall_improvement = (results_v1['mae_normal'] - results_v2['mae_normal']) / results_v1['mae_normal'] * 100

    if overall_improvement > 5:
        print(f"\n v2 MODEL DAHA IYI!")
        print(f"    Normal fiyatlar icin {overall_improvement:.1f}% iyilesme")
        print(f"    Kullanim onerisi: v2 modelini kullan")
    elif overall_improvement > 0:
        print(f"\n v2 HAFIF DAHA IYI")
        print(f"    {overall_improvement:.1f}% iyilesme (minör)")
        print(f"    Her iki model de kullanilabilir")
    else:
        print(f"\n MODELLER BENZER")
        print(f"    Anlamli fark yok")
        print(f"    v1 (daha basit) tercih edilebilir")

    print("="*70)

if __name__ == "__main__":
    main()
