#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Feature Engineering Pipeline
=============================

Bu modül, MCP fiyat tahmini için gerekli feature'ları hazırlar.
Hem Prophet hem de XGBoost modelleri bu modülü kullanır.

Özellikler:
- 3 tabloyu birleştirir (MCP + Consumption + Generation)
- Talep/arz bazlı feature'lar hesaplar
- Lag feature'lar oluşturur
- Time-based train/test split yapar
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime, timedelta

# Veri tabanı yolu
DB_PATH = os.path.join(os.path.dirname(__file__), '../../data/energy.db')


def load_combined_data(end_date=None):
    """
    3 tabloyu (MCP, Consumption, Generation) birleştirerek yükler.
    
    Args:
        end_date (str, optional): Bu tarihe KADAR veri yükle (dahil değil!).
                                  Format: 'YYYY-MM-DD' veya 'YYYY-MM-DD HH:MM:SS'
                                  None ise tüm veriyi yükler.
    Returns:
        pd.DataFrame: Birleştirilmiş veri seti
    """
    print("[*] Birleştirilmiş veri yükleniyor (MCP + Consumption + Generation)...")
    
    if end_date:
        print(f"[*] Data leakage önleme: {end_date} tarihine KADAR veri kullanılacak")
    
    conn = sqlite3.connect(DB_PATH)
    
    # 3 tabloyu JOIN ile birleştir
    # LEFT JOIN kullanıyoruz çünkü bazı saatlerde consumption/generation verisi eksik olabilir
    query = """
        SELECT 
            m.date as ds,
            m.price as y,
            m.hour,
            c.consumption,
            g.total as generation_total,
            g.solar,
            g.wind,
            g.hydro,
            g.natural_gas,
            g.lignite,
            g.geothermal,
            g.biomass
        FROM mcp_data m
        LEFT JOIN consumption_data c 
            ON DATE(m.date) = DATE(c.date) AND m.hour = c.hour
        LEFT JOIN generation_data g 
            ON DATE(m.date) = DATE(g.date) AND m.hour = g.hour
    """
    
    if end_date:
        query += f" WHERE m.date < '{end_date}'"
    
    query += " ORDER BY m.date"
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Tarih formatını düzelt
    df['ds'] = pd.to_datetime(df['ds']).dt.tz_localize(None)
    
    print(f"[+] {len(df)} kayıt yüklendi")
    print(f"[*] Tarih aralığı: {df['ds'].min()} -> {df['ds'].max()}")
    
    # Eksik veri kontrolü
    missing_consumption = df['consumption'].isna().sum()
    missing_generation = df['generation_total'].isna().sum()
    
    if missing_consumption > 0:
        print(f"[!] Uyarı: {missing_consumption} satırda consumption verisi eksik")
    if missing_generation > 0:
        print(f"[!] Uyarı: {missing_generation} satırda generation verisi eksik")
    
    return df


def engineer_features(df):
    """
    Ham veriden feature'lar oluşturur.
    
    Prophet ve XGBoost için ortak feature engineering.
    
    Args:
        df: load_combined_data() çıktısı
        
    Returns:
        pd.DataFrame: Feature'lar eklenmiş veri seti
    """
    print("\n[*] Feature engineering yapılıyor...")
    
    df = df.copy()
    
    # ========================================
    # 1. ZAMAN BAZLI FEATURE'LAR
    # ========================================
    
    # Saat bilgisi (0-23)
    df['hour'] = df['ds'].dt.hour
    
    # Haftanın günü (0=Pazartesi, 6=Pazar)
    df['day_of_week'] = df['ds'].dt.dayofweek
    
    # Hafta sonu mu?
    df['is_weekend'] = (df['ds'].dt.dayofweek >= 5).astype(int)
    
    # Peak saat mi? (Sabah 8-10, Akşam 18-21)
    df['is_peak_hour'] = df['hour'].isin([8, 9, 10, 18, 19, 20, 21]).astype(int)
    
    # Gündüz mü? (Güneş var, 10:00-16:00)
    df['is_daytime'] = df['hour'].isin(range(10, 16)).astype(int)
    
    # Ayın günü
    df['day_of_month'] = df['ds'].dt.day
    
    # Ay
    df['month'] = df['ds'].dt.month
    
    # ========================================
    # 2. ARZ/TALEP BAZLI FEATURE'LAR
    # ========================================
    
    # Eksik verileri doldur (forward fill + backward fill)
    df['consumption'] = df['consumption'].fillna(method='ffill').fillna(method='bfill')
    df['generation_total'] = df['generation_total'].fillna(method='ffill').fillna(method='bfill')
    
    # Arz-talep farkı (pozitif = fazla üretim, negatif = fazla talep)
    df['supply_demand_gap'] = df['generation_total'] - df['consumption']
    
    # ========================================
    # 3. YENİLENEBİLİR ENERJİ FEATURE'LARI
    # ========================================
    
    # Eksik değerleri doldur
    for col in ['solar', 'wind', 'hydro', 'natural_gas', 'lignite']:
        df[col] = df[col].fillna(0)
    
    # Yenilenebilir üretim (güneş + rüzgar)
    df['renewable'] = df['solar'] + df['wind']
    
    # Yenilenebilir oranı (0-1 arası)
    df['renewable_ratio'] = np.where(
        df['generation_total'] > 0,
        df['renewable'] / df['generation_total'],
        0
    )
    
    # Fosil yakıt üretimi (doğalgaz + linyit)
    df['fossil'] = df['natural_gas'] + df['lignite']
    
    # Fosil oranı (0-1 arası)
    df['fossil_ratio'] = np.where(
        df['generation_total'] > 0,
        df['fossil'] / df['generation_total'],
        0
    )
    
    # Hidroelektrik oranı
    df['hydro_ratio'] = np.where(
        df['generation_total'] > 0,
        df['hydro'] / df['generation_total'],
        0
    )
    
    # ========================================
    # 4. LAG FEATURE'LAR (GEÇMİŞ DEĞERLER)
    # ========================================
    
    # 1 saat önceki fiyat
    df['price_lag_1h'] = df['y'].shift(1)
    
    # 24 saat önceki fiyat (dünün aynı saati)
    df['price_lag_24h'] = df['y'].shift(24)
    
    # 168 saat önceki fiyat (geçen haftanın aynı saati)
    df['price_lag_168h'] = df['y'].shift(168)
    
    # 24 saatlik hareketli ortalama
    df['price_rolling_24h'] = df['y'].rolling(window=24, min_periods=1).mean()
    
    # 24 saatlik standart sapma (volatilite)
    df['price_std_24h'] = df['y'].rolling(window=24, min_periods=1).std()
    
    # Consumption lag
    df['consumption_lag_24h'] = df['consumption'].shift(24)
    
    # ========================================
    # 5. İLK SATIRLARI TEMİZLE (LAG'DAN DOLAYI NaN)
    # ========================================
    
    # İlk 168 satırı (1 hafta) at çünkü lag feature'lar NaN olacak
    initial_rows = len(df)
    df = df.dropna(subset=['price_lag_168h'])
    dropped_rows = initial_rows - len(df)
    
    print(f"\n[+] Feature'lar oluşturuldu:")
    print(f"   - Zaman bazlı: hour, day_of_week, is_weekend, is_peak_hour, is_daytime")
    print(f"   - Arz/Talep: consumption, generation_total, supply_demand_gap")
    print(f"   - Yenilenebilir: renewable, renewable_ratio, fossil, fossil_ratio")
    print(f"   - Lag: price_lag_1h, price_lag_24h, price_lag_168h, price_rolling_24h")
    print(f"   - {dropped_rows} satır lag nedeniyle silindi (ilk 1 hafta)")
    print(f"   - Final veri seti: {len(df)} satır")
    
    return df


def get_prophet_features():
    """Prophet modeli için kullanılacak regressor listesi"""
    return [
        'hour',
        'is_weekend', 
        'is_peak_hour',
        'is_daytime',
        'day_of_week',
        'consumption',
        'supply_demand_gap',
        'renewable_ratio',
        'fossil_ratio',
        'price_lag_24h',
    ]


def get_xgboost_features():
    """XGBoost modeli için kullanılacak feature listesi"""
    return [
        # Zaman bazlı
        'hour',
        'day_of_week',
        'day_of_month',
        'month',
        'is_weekend',
        'is_peak_hour',
        'is_daytime',
        
        # Arz/Talep
        'consumption',
        'generation_total',
        'supply_demand_gap',
        
        # Yenilenebilir
        'renewable',
        'renewable_ratio',
        'fossil',
        'fossil_ratio',
        'hydro_ratio',
        
        # Lag features
        'price_lag_1h',
        'price_lag_24h',
        'price_lag_168h',
        'price_rolling_24h',
        'price_std_24h',
        'consumption_lag_24h',
    ]


def prepare_future_features(df, future_dates):
    """
    Gelecek tahmin için feature'ları hazırlar.
    
    Prophet predict() için future dataframe'e feature ekleme.
    XGBoost için de tüm gerekli feature'ları oluşturur.
    
    Args:
        df: Mevcut veri seti (son değerleri almak için)
        future_dates: Prophet'in oluşturduğu future dataframe
        
    Returns:
        pd.DataFrame: Feature'lar eklenmiş future dataframe
    """
    future = future_dates.copy()
    
    # ========================================
    # 1. ZAMAN BAZLI FEATURE'LAR
    # ========================================
    future['hour'] = future['ds'].dt.hour
    future['day_of_week'] = future['ds'].dt.dayofweek
    future['is_weekend'] = (future['ds'].dt.dayofweek >= 5).astype(int)
    future['is_peak_hour'] = future['hour'].isin([8, 9, 10, 18, 19, 20, 21]).astype(int)
    future['is_daytime'] = future['hour'].isin(range(10, 16)).astype(int)
    future['day_of_month'] = future['ds'].dt.day
    future['month'] = future['ds'].dt.month
    
    # ========================================
    # 2. ARZ/TALEP FEATURE'LAR (saatlik ortalama kullan)
    # ========================================
    hourly_avg_consumption = df.groupby('hour')['consumption'].mean()
    hourly_avg_generation = df.groupby('hour')['generation_total'].mean()
    hourly_avg_renewable_ratio = df.groupby('hour')['renewable_ratio'].mean()
    hourly_avg_fossil_ratio = df.groupby('hour')['fossil_ratio'].mean()
    hourly_avg_hydro_ratio = df.groupby('hour')['hydro_ratio'].mean()
    hourly_avg_renewable = df.groupby('hour')['renewable'].mean()
    hourly_avg_fossil = df.groupby('hour')['fossil'].mean()
    
    future['consumption'] = future['hour'].map(hourly_avg_consumption)
    future['generation_total'] = future['hour'].map(hourly_avg_generation)
    future['supply_demand_gap'] = future['generation_total'] - future['consumption']
    future['renewable_ratio'] = future['hour'].map(hourly_avg_renewable_ratio)
    future['fossil_ratio'] = future['hour'].map(hourly_avg_fossil_ratio)
    future['hydro_ratio'] = future['hour'].map(hourly_avg_hydro_ratio)
    future['renewable'] = future['hour'].map(hourly_avg_renewable)
    future['fossil'] = future['hour'].map(hourly_avg_fossil)
    
    # ========================================
    # 3. LAG FEATURE'LAR (son bilinen değerler)
    # ========================================
    last_price = df['y'].iloc[-1]
    last_24h_prices = df['y'].tail(24)
    last_168h_prices = df['y'].tail(168)
    
    future['price_lag_1h'] = last_price
    future['price_lag_24h'] = last_24h_prices.mean()
    future['price_lag_168h'] = last_168h_prices.mean()
    future['price_rolling_24h'] = last_24h_prices.mean()
    future['price_std_24h'] = last_24h_prices.std()
    future['consumption_lag_24h'] = df['consumption'].tail(24).mean()
    
    return future


def train_test_split_timeseries(df, test_days=30):
    """
    Time-series için train/test split yapar.
    
    Önemli: Zaman serilerinde random split YAPILMAZ! 
    Son N gün test, geri kalanı train olmalı.
    
    Args:
        df: Feature'lar eklenmiş veri seti
        test_days: Test için ayrılacak gün sayısı
        
    Returns:
        tuple: (train_df, test_df)
    """
    split_date = df['ds'].max() - timedelta(days=test_days)
    
    train = df[df['ds'] <= split_date].copy()
    test = df[df['ds'] > split_date].copy()
    
    print(f"\n[*] Train/Test split:")
    print(f"   - Train: {len(train)} satır ({train['ds'].min()} -> {train['ds'].max()})")
    print(f"   - Test:  {len(test)} satır ({test['ds'].min()} -> {test['ds'].max()})")
    
    return train, test


# Test amaçlı çalıştırma
if __name__ == "__main__":
    print("=" * 60)
    print("Feature Engineering Test")
    print("=" * 60)
    
    # Veri yükle
    df = load_combined_data()
    
    # Feature'ları oluştur
    df = engineer_features(df)
    
    # Train/test split
    train, test = train_test_split_timeseries(df)
    
    # Feature listelerini göster
    print("\n[*] Prophet regressors:", get_prophet_features())
    print("[*] XGBoost features:", get_xgboost_features())
    
    # İlk birkaç satırı göster
    print("\n[*] Örnek veriler:")
    print(df[['ds', 'y', 'consumption', 'renewable_ratio', 'price_lag_24h']].head(10))
    
    print("\n[+] Feature engineering test tamamlandı!")
