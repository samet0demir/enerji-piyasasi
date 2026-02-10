#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
v2 Model Test - Extreme price handling kontrolu
"""

import pandas as pd
import numpy as np
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

# v2 model egitimi yaptik, simdi manuel test yapalim
# Model dosyasini yukleyemiyoruz (bug), ama egitim scriptini import edebiliriz

from train_prophet_improved import load_data, create_holidays, add_extreme_low_regressor
from prophet import Prophet

def test_v2_performance():
    """v2 modelini test et"""
    print("="*70)
    print("v2 MODEL TEST - Extreme Price Handling")
    print("="*70)

    # Veri yukle
    df = load_data()
    df = add_extreme_low_regressor(df)

    # Son 60 gun test
    test_start = df['ds'].max() - timedelta(days=60)
    train = df[df['ds'] <= test_start]
    test = df[df['ds'] > test_start]

    print(f"\n[*] Train: {len(train)} kayit")
    print(f"[*] Test:  {len(test)} kayit")

    # Model egit
    print(f"\n[*] v2 model egitiliyor (extreme_low_risk regressor ile)...")

    holidays = create_holidays()

    model = Prophet(
        holidays=holidays,
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True,
        changepoint_prior_scale=0.05,
        holidays_prior_scale=10.0,
        seasonality_prior_scale=10.0,
    )
    model.add_country_holidays('TR')
    model.add_regressor('extreme_low_risk', prior_scale=15.0)

    model.fit(train[['ds', 'y', 'extreme_low_risk']])

    print("[+] Egitim tamamlandi!")

    # Tahmin
    print(f"\n[*] Test seti icin tahmin yapiliyor...")
    test_with_reg = add_extreme_low_regressor(test)
    forecast = model.predict(test_with_reg[['ds', 'extreme_low_risk']])

    # Degerlendir
    y_true = test['y'].values
    y_pred = forecast['yhat'].values

    # Tum veri
    mae_all = np.mean(np.abs(y_true - y_pred))
    rmse_all = np.sqrt(np.mean((y_true - y_pred)**2))

    # Normal (>=100)
    normal_mask = y_true >= 100
    mae_normal = np.mean(np.abs(y_true[normal_mask] - y_pred[normal_mask]))
    mape_normal = np.mean(np.abs((y_true[normal_mask] - y_pred[normal_mask]) / y_true[normal_mask])) * 100

    # Ekstrem (<100)
    extreme_mask = y_true < 100
    extreme_count = extreme_mask.sum()
    mae_extreme = np.mean(np.abs(y_true[extreme_mask] - y_pred[extreme_mask])) if extreme_count > 0 else 0

    # Rapor
    print(f"\n{'='*70}")
    print("PERFORMANS SONUCLARI (v2 Model)")
    print(f"{'='*70}")

    print(f"\nTum Veri ({len(test)} kayit):")
    print(f"  MAE:  {mae_all:.2f} TRY")
    print(f"  RMSE: {rmse_all:.2f} TRY")

    print(f"\nNormal Fiyatlar (>= 100 TRY): {normal_mask.sum()} kayit")
    print(f"  MAE:  {mae_normal:.2f} TRY")
    print(f"  MAPE: {mape_normal:.2f}%")

    print(f"\nEkstrem Dusuk (<100 TRY): {extreme_count} kayit")
    if extreme_count > 0:
        print(f"  MAE:  {mae_extreme:.2f} TRY")

        # Ekstrem fiyatlarda en iyi/kotu tahminler
        extreme_errors = np.abs(y_true[extreme_mask] - y_pred[extreme_mask])
        print(f"  En iyi tahmin hatasi: {extreme_errors.min():.2f} TRY")
        print(f"  En kotu tahmin hatasi: {extreme_errors.max():.2f} TRY")

        # Ornekler
        print(f"\n  Ornek tahminler (ilk 5 ekstrem dusuk):")
        extreme_indices = np.where(extreme_mask)[0][:5]
        for idx in extreme_indices:
            print(f"    Gercek: {y_true[idx]:.2f} TRY, Tahmin: {y_pred[idx]:.2f} TRY, Hata: {abs(y_true[idx]-y_pred[idx]):.2f} TRY")

    # Baseline ile karsilastirma
    print(f"\n{'='*70}")
    print("BASELINE KARSILASTIRMA")
    print(f"{'='*70}")

    # Naive baseline: "yarin = bugun"
    naive_pred = np.roll(y_true, 1)
    naive_pred[0] = y_true[0]  # ilk deger icin
    naive_mae = np.mean(np.abs(y_true - naive_pred))

    print(f"\nNaive Model (yarin = bugun):")
    print(f"  MAE: {naive_mae:.2f} TRY")

    improvement = ((naive_mae - mae_all) / naive_mae) * 100
    print(f"\nv2 Prophet Iyilesmesi:")
    print(f"  {improvement:.1f}% daha iyi!")

    # Sonuc
    print(f"\n{'='*70}")
    print("DEGERLENDIRME")
    print(f"{'='*70}")

    print(f"\nAkademik Standartlar:")
    if mape_normal < 10:
        print(f"  COKUYI: MAPE {mape_normal:.1f}% < %10")
    elif mape_normal < 15:
        print(f"  IYI: MAPE {mape_normal:.1f}% < %15")
    elif mape_normal < 20:
        print(f"  KABUL EDILEBILIR: MAPE {mape_normal:.1f}% < %20")
    else:
        print(f"  ZAYIF: MAPE {mape_normal:.1f}% > %20")

    print(f"\nEkstrem Fiyat Yonetimi:")
    if extreme_count > 0 and mae_extreme < 500:
        print(f"  IYI: Ekstrem fiyatlar icin MAE {mae_extreme:.0f} TRY")
    elif extreme_count > 0:
        print(f"  ORTA: Ekstrem fiyatlar icin MAE {mae_extreme:.0f} TRY")
    else:
        print(f"  Test setinde ekstrem fiyat yok")

    print("="*70)

    return {
        'mae_all': mae_all,
        'mae_normal': mae_normal,
        'mape_normal': mape_normal,
        'mae_extreme': mae_extreme,
        'improvement_vs_baseline': improvement
    }

if __name__ == "__main__":
    results = test_v2_performance()
