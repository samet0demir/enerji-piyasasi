#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Iyilestirilmis Prophet Modeli - Extreme Fiyat Handling
"""

import pandas as pd
import numpy as np
from prophet import Prophet
import sqlite3
import os

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/prophet_model_v2.json')

def load_data():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT date as ds, price as y FROM mcp_data ORDER BY date"
    df = pd.read_sql_query(query, conn)
    conn.close()
    df['ds'] = pd.to_datetime(df['ds']).dt.tz_localize(None)
    return df

def create_holidays():
    """Tatilleri olustur"""
    holidays = pd.DataFrame({
        'holiday': [
            'Ramazan_Bayrami', 'Ramazan_Bayrami', 'Ramazan_Bayrami',
            'Ramazan_Bayrami', 'Ramazan_Bayrami', 'Ramazan_Bayrami',
            'Ramazan_Bayrami', 'Ramazan_Bayrami', 'Ramazan_Bayrami',
            'Kurban_Bayrami', 'Kurban_Bayrami', 'Kurban_Bayrami',
            'Kurban_Bayrami', 'Kurban_Bayrami',
            'Ramazan_Bayrami', 'Ramazan_Bayrami', 'Ramazan_Bayrami',
            'Kurban_Bayrami', 'Kurban_Bayrami', 'Kurban_Bayrami',
            'Kurban_Bayrami', 'Kurban_Bayrami',
        ],
        'ds': pd.to_datetime([
            '2024-04-06', '2024-04-07', '2024-04-08', '2024-04-09', '2024-04-10',
            '2024-04-11', '2024-04-12', '2024-04-13', '2024-04-14',
            '2024-06-15', '2024-06-16', '2024-06-17', '2024-06-18', '2024-06-19',
            '2025-03-29', '2025-03-30', '2025-04-01',
            '2025-06-05', '2025-06-06', '2025-06-07', '2025-06-08', '2025-06-09',
        ]),
        'lower_window': 0,
        'upper_window': 1,
    })
    return holidays

def add_extreme_low_regressor(df):
    """
    Ekstrem dusuk fiyat regressoru ekle
    Pazar + ogle saati kombinasyonu
    """
    df = df.copy()

    # Pazar gunu + ogle saatleri (10-14)
    df['is_sunday'] = df['ds'].dt.dayofweek == 6
    df['is_midday'] = df['ds'].dt.hour.isin([10, 11, 12, 13, 14])
    df['extreme_low_risk'] = (df['is_sunday'] & df['is_midday']).astype(int)

    return df

def train_improved_model():
    """Iyilestirilmis model egitimi"""
    print("="*60)
    print("Iyilestirilmis Prophet Model Egitimi (v2)")
    print("="*60)

    # Veri yukle
    df = load_data()
    print(f"\n[*] Veri yuklendi: {len(df)} kayit")

    # Extreme low regressor ekle
    df = add_extreme_low_regressor(df)

    # Tatiller
    holidays = create_holidays()

    # Model olustur
    print(f"\n[*] Model olusturuluyor...")
    model = Prophet(
        holidays=holidays,
        daily_seasonality=True,
        weekly_seasonality=True,
        yearly_seasonality=True,
        changepoint_prior_scale=0.05,
        holidays_prior_scale=10.0,
        seasonality_prior_scale=10.0,
        interval_width=0.95,
    )

    # Turkiye tatilleri
    model.add_country_holidays('TR')

    # Extreme low regressor ekle
    model.add_regressor('extreme_low_risk', prior_scale=15.0)

    print("[*] Egitim basliyor...")
    model.fit(df[['ds', 'y', 'extreme_low_risk']])

    print("[+] Egitim tamamlandi!")

    # Model kaydet
    from prophet.serialize import model_to_json
    with open(MODEL_PATH, 'w') as f:
        f.write(model_to_json(model))

    print(f"\n[+] Model kaydedildi: {MODEL_PATH}")
    print("="*60)

    return model

if __name__ == "__main__":
    model = train_improved_model()
