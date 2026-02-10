#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mevcut modelin farklı zaman dilimlerindeki performansını kontrol eder
"""

import pandas as pd
import numpy as np
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

def load_model():
    """Eğitilmiş modeli yükle"""
    with open(MODEL_PATH, 'r') as f:
        model = model_from_json(f.read())
    return model

def evaluate_period(model, test_data, period_name):
    """Belirli bir dönem için tahmin yap ve değerlendir"""
    print(f"\n{'='*60}")
    print(f"Donem: {period_name}")
    print(f"{'='*60}")
    print(f"Tarih araligi: {test_data['ds'].min()} -> {test_data['ds'].max()}")
    print(f"Kayit sayisi: {len(test_data)}")

    # Tahmin
    forecast = model.predict(test_data[['ds']])

    # Metrikler
    y_true = test_data['y'].values
    y_pred = forecast['yhat'].values

    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))

    mask = y_true != 0
    mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.sum() > 0 else 0

    # Residual analizi
    residuals = y_true - y_pred
    residual_mean = np.mean(residuals)
    residual_std = np.std(residuals)

    print(f"\nPerformans Metrikleri:")
    print(f"  MAE:  {mae:.2f} TRY")
    print(f"  RMSE: {rmse:.2f} TRY")
    print(f"  MAPE: {mape:.2f}%")

    print(f"\nResidual Analizi:")
    print(f"  Ortalama hata: {residual_mean:.2f} TRY (0'a yakin olmali)")
    print(f"  Standart sapma: {residual_std:.2f} TRY")

    return {
        'period': period_name,
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'residual_mean': residual_mean,
        'residual_std': residual_std
    }

def main():
    print("="*60)
    print("Overfitting Kontrolu - Mevcut Modelin Tutarliligi")
    print("="*60)

    # Model ve veri yükle
    print("\n[*] Model yukleniyor...")
    model = load_model()
    print("[*] Veri yukleniyor...")
    df = load_data()

    # Farklı zaman dilimlerini tanımla
    periods = []

    # İlk 3 ay (Ekim-Aralık 2023)
    p1_start = df['ds'].min()
    p1_end = p1_start + timedelta(days=90)
    periods.append({
        'name': 'Ilk 3 Ay (2023 Ekim-Aralik)',
        'data': df[(df['ds'] >= p1_start) & (df['ds'] < p1_end)]
    })

    # Orta dönem - Yaz 2024 (Haziran-Ağustos)
    p2_start = pd.to_datetime('2024-06-01')
    p2_end = pd.to_datetime('2024-09-01')
    periods.append({
        'name': 'Yaz Donemi (2024 Haziran-Agustos)',
        'data': df[(df['ds'] >= p2_start) & (df['ds'] < p2_end)]
    })

    # Kış 2024-2025 (Aralık-Şubat)
    p3_start = pd.to_datetime('2024-12-01')
    p3_end = pd.to_datetime('2025-03-01')
    periods.append({
        'name': 'Kis Donemi (2024 Aralik-2025 Subat)',
        'data': df[(df['ds'] >= p3_start) & (df['ds'] < p3_end)]
    })

    # Son 60 gün
    p4_start = df['ds'].max() - timedelta(days=60)
    periods.append({
        'name': 'Son 60 Gun (2025 Agustos-Ekim)',
        'data': df[df['ds'] >= p4_start]
    })

    # Her dönemi değerlendir
    results = []
    for period in periods:
        if len(period['data']) > 0:
            result = evaluate_period(model, period['data'], period['name'])
            results.append(result)

    # Sonuçları özetle
    print(f"\n{'='*60}")
    print("GENEL DEGERLENDIRME")
    print(f"{'='*60}")

    mapes = [r['mape'] for r in results]
    avg_mape = np.mean(mapes)
    std_mape = np.std(mapes)
    cv = (std_mape / avg_mape) * 100 if avg_mape > 0 else 0

    print(f"\nDonemler Arasi MAPE Karsilastirmasi:")
    for r in results:
        deviation = abs(r['mape'] - avg_mape)
        status = "✅" if deviation < std_mape else "⚠️"
        print(f"  {status} {r['period']:40s}: {r['mape']:6.2f}%")

    print(f"\nIstatistikler:")
    print(f"  Ortalama MAPE: {avg_mape:.2f}%")
    print(f"  Standart Sapma: {std_mape:.2f}%")
    print(f"  Varyasyon Katsayisi (CV): {cv:.2f}%")

    print(f"\nResidual Bias Kontrolu:")
    residual_means = [r['residual_mean'] for r in results]
    avg_bias = np.mean([abs(r) for r in residual_means])
    print(f"  Ortalama mutlak bias: {avg_bias:.2f} TRY")

    print(f"\n{'='*60}")
    print("SONUC:")
    print(f"{'='*60}")

    # Overfitting değerlendirmesi
    if cv < 15:
        print("✅ OVERFITTING YOK")
        print("   Model farkli zaman dilimlerinde tutarli performans gosteriyor.")
    elif cv < 30:
        print("⚠️  HAFIF OVERFITTING")
        print("   Model genelde iyi ama bazi donemlerde performans dususu var.")
    else:
        print("❌ CIDDI OVERFITTING")
        print("   Model belirli donemlere asiri uymus, genelleme yapamıyor.")

    # Bias kontrolü
    if avg_bias < 100:
        print(f"\n✅ BIAS YOK (Ortalama bias: {avg_bias:.2f} TRY)")
        print("   Model sistematik hata yapmıyor.")
    else:
        print(f"\n⚠️  BIAS VAR (Ortalama bias: {avg_bias:.2f} TRY)")
        print("   Model sistematik olarak yuksek/dusuk tahmin yapiyor.")

    print("="*60)

if __name__ == "__main__":
    main()
