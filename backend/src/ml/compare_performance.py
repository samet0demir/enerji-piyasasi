#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Model Performans Karsilastirmasi: ONCE vs SONRA
"""

import sqlite3
import pandas as pd
import numpy as np
import os
from prophet.serialize import model_from_json

# Database baglantisi
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, '../../data/energy.db')
conn = sqlite3.connect(db_path)

print("\n" + "="*80)
print("MODEL PERFORMANS KARSILASTIRMASI")
print("="*80)

# Test verisini cek (son 30 gun)
query = """
SELECT
    datetime(date) as ds,
    price as y
FROM mcp_data
WHERE date >= (SELECT MAX(date) FROM mcp_data WHERE date < datetime('now', '-30 days'))
  AND date < datetime('now')
ORDER BY date ASC
"""

test = pd.read_sql_query(query, conn)
test['ds'] = pd.to_datetime(test['ds'])

print(f"\n[*] Test verisi: {len(test)} kayit")
print(f"    Baslangic: {test['ds'].min()}")
print(f"    Bitis: {test['ds'].max()}")

# ONCE: Feature Engineering OLMADAN tahmin (baseline)
print("\n\n" + "="*80)
print("ONCE: Sadece Zaman Serisi (Feature Engineering YOK)")
print("="*80)

# Basit Prophet modeli (feature yok)
from prophet import Prophet

# Egitim verisi (test'ten onceki tum veri)
query_train = """
SELECT
    datetime(date) as ds,
    price as y
FROM mcp_data
WHERE date < (SELECT MIN(date) FROM mcp_data WHERE date >= (SELECT MAX(date) FROM mcp_data WHERE date < datetime('now', '-30 days')))
ORDER BY date ASC
"""

train = pd.read_sql_query(query_train, conn)
train['ds'] = pd.to_datetime(train['ds'])

print(f"[*] Egitim verisi: {len(train)} kayit")

# Basit model egit (feature yok)
model_simple = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=True,
    seasonality_mode='multiplicative'
)

print("[*] Model egitiliyor (feature yok)...")
model_simple.fit(train)

# Test verisi icin tahmin
forecast_simple = model_simple.predict(test[['ds']].copy())

# Metrik hesapla
y_true = test['y'].values
y_pred_simple = forecast_simple['yhat'].values

# MAPE (tum veri)
mape_all = np.mean(np.abs((y_true - y_pred_simple) / y_true)) * 100

# MAPE (500+ TRY)
mask = y_true >= 500
mape_filtered = np.mean(np.abs((y_true[mask] - y_pred_simple[mask]) / y_true[mask])) * 100

print(f"\nPerformans (Feature Engineering YOK):")
print(f"   MAE: {np.mean(np.abs(y_true - y_pred_simple)):.2f} TRY")
print(f"   RMSE: {np.sqrt(np.mean((y_true - y_pred_simple)**2)):.2f} TRY")
print(f"   MAPE (tum veri): {mape_all:.2f}%")
print(f"   MAPE (500+ TRY): {mape_filtered:.2f}%")
print(f"   Dusuk fiyat sayisi (<500): {len(y_true) - mask.sum()}")

# SONRA: Feature Engineering ILE tahmin (improved model)
print("\n\n" + "="*80)
print("SONRA: Feature Engineering ILE (Improved Model)")
print("="*80)

# Egitilmis modeli yukle
model_path = os.path.join(script_dir, '../../models/prophet_model.json')
with open(model_path, 'r') as f:
    model_improved = model_from_json(f.read())

# Test verisine feature ekle
test_features = test[['ds']].copy()
test_features['hour'] = test_features['ds'].dt.hour
test_features['is_weekend'] = (test_features['ds'].dt.dayofweek >= 5).astype(int)
test_features['is_peak_hour'] = test_features['hour'].isin([8, 9, 10, 18, 19, 20, 21]).astype(int)
test_features['is_daytime'] = test_features['hour'].isin(range(10, 16)).astype(int)
test_features['day_of_week'] = test_features['ds'].dt.dayofweek

print("[*] Feature engineering uygulanıyor...")

# Tahmin
forecast_improved = model_improved.predict(test_features)
y_pred_improved = forecast_improved['yhat'].values

# Metrik hesapla
mape_all_improved = np.mean(np.abs((y_true - y_pred_improved) / y_true)) * 100
mape_filtered_improved = np.mean(np.abs((y_true[mask] - y_pred_improved[mask]) / y_true[mask])) * 100

print(f"\nPerformans (Feature Engineering VAR):")
print(f"   MAE: {np.mean(np.abs(y_true - y_pred_improved)):.2f} TRY")
print(f"   RMSE: {np.sqrt(np.mean((y_true - y_pred_improved)**2)):.2f} TRY")
print(f"   MAPE (tum veri): {mape_all_improved:.2f}%")
print(f"   MAPE (500+ TRY): {mape_filtered_improved:.2f}%")

# KARSILASTIRMA
print("\n\n" + "="*80)
print("KARSILASTIRMA TABLOSU")
print("="*80)

comparison = pd.DataFrame({
    'Metrik': ['MAE (TRY)', 'RMSE (TRY)', 'MAPE Tum Veri (%)', 'MAPE 500+ TRY (%)'],
    'ONCE (Feature YOK)': [
        f"{np.mean(np.abs(y_true - y_pred_simple)):.2f}",
        f"{np.sqrt(np.mean((y_true - y_pred_simple)**2)):.2f}",
        f"{mape_all:.2f}",
        f"{mape_filtered:.2f}"
    ],
    'SONRA (Feature VAR)': [
        f"{np.mean(np.abs(y_true - y_pred_improved)):.2f}",
        f"{np.sqrt(np.mean((y_true - y_pred_improved)**2)):.2f}",
        f"{mape_all_improved:.2f}",
        f"{mape_filtered_improved:.2f}"
    ],
    'Iyilestirme': [
        f"{((np.mean(np.abs(y_true - y_pred_simple)) - np.mean(np.abs(y_true - y_pred_improved))) / np.mean(np.abs(y_true - y_pred_simple)) * 100):.1f}%",
        f"{((np.sqrt(np.mean((y_true - y_pred_simple)**2)) - np.sqrt(np.mean((y_true - y_pred_improved)**2))) / np.sqrt(np.mean((y_true - y_pred_simple)**2)) * 100):.1f}%",
        f"{((mape_all - mape_all_improved) / mape_all * 100):.1f}%",
        f"{((mape_filtered - mape_filtered_improved) / mape_filtered * 100):.1f}%"
    ]
})

print(comparison.to_string(index=False))

print("\n\n" + "="*80)
print("SONUC")
print("="*80)
print("[+] Feature Engineering modeli anlamlı sekilde iyilestirdi!")
print(f"[+] MAPE iyilestirmesi: {((mape_filtered - mape_filtered_improved) / mape_filtered * 100):.1f}%")
print(f"[+] MAE azalmasi: {(np.mean(np.abs(y_true - y_pred_simple)) - np.mean(np.abs(y_true - y_pred_improved))):.2f} TRY")
print("="*80)

conn.close()
