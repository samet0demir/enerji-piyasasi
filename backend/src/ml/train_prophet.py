#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ MCP Fiyat Tahmini - Multivariate Prophet Model Eğitimi
=============================================================

GÜNCELLEME: Multivariate versiyona geçildi!

Bu script:
1. features.py modülünü kullanarak birleştirilmiş veri yükler
2. Consumption, generation, renewable_ratio gibi exogenous regressor'lar ekler
3. Türkiye resmi tatillerini otomatik ekler
4. Ramazan ve Kurban Bayramı tarihlerini manuel ekler
5. Prophet modelini eğitir ve kaydeder
6. Model performansını değerlendirir

Eski univariate model: train_prophet_legacy.py olarak yedeklendi
"""

import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings('ignore')

# Feature engineering modülünü import et
from features import (
    load_combined_data, 
    engineer_features, 
    get_prophet_features,
    train_test_split_timeseries
)

# Model yolu
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/prophet_model.json')


def create_turkish_holidays():
    """
    Türkiye'ye özel tatil günlerini oluşturur

    Returns:
        pd.DataFrame: Tatil tarihleri ve isimleri
    """
    print("\n[*] Türk tatilleri oluşturuluyor...")

    holidays = pd.DataFrame({
        'holiday': [
            # 2024 Ramazan Bayramı (6-14 Nisan, uzatmalı)
            'Ramazan_Bayrami', 'Ramazan_Bayrami', 'Ramazan_Bayrami',
            'Ramazan_Bayrami', 'Ramazan_Bayrami', 'Ramazan_Bayrami',
            'Ramazan_Bayrami', 'Ramazan_Bayrami', 'Ramazan_Bayrami',

            # 2024 Kurban Bayramı (15-19 Haziran)
            'Kurban_Bayrami', 'Kurban_Bayrami', 'Kurban_Bayrami',
            'Kurban_Bayrami', 'Kurban_Bayrami',

            # 2025 Ramazan Bayramı (29 Mart - 1 Nisan)
            'Ramazan_Bayrami', 'Ramazan_Bayrami', 'Ramazan_Bayrami',

            # 2025 Kurban Bayramı (5-9 Haziran)
            'Kurban_Bayrami', 'Kurban_Bayrami', 'Kurban_Bayrami',
            'Kurban_Bayrami', 'Kurban_Bayrami',
        ],
        'ds': pd.to_datetime([
            # 2024 Ramazan (9 günlük uzatma)
            '2024-04-06', '2024-04-07', '2024-04-08', '2024-04-09', '2024-04-10',
            '2024-04-11', '2024-04-12', '2024-04-13', '2024-04-14',

            # 2024 Kurban
            '2024-06-15', '2024-06-16', '2024-06-17', '2024-06-18', '2024-06-19',

            # 2025 Ramazan
            '2025-03-29', '2025-03-30', '2025-04-01',

            # 2025 Kurban
            '2025-06-05', '2025-06-06', '2025-06-07', '2025-06-08', '2025-06-09',
        ]),
        'lower_window': 0,
        'upper_window': 1,  # Bayram öncesi gün etkisini de yakala
    })

    print(f"[+] {len(holidays)} bayram günü eklendi:")
    print(f"   - Ramazan Bayramı: {len(holidays[holidays['holiday']=='Ramazan_Bayrami'])} gün")
    print(f"   - Kurban Bayramı: {len(holidays[holidays['holiday']=='Kurban_Bayrami'])} gün")

    return holidays


def train_prophet_model(df, holidays):
    """
    Multivariate Prophet modelini eğitir

    Args:
        df: Eğitim verisi (feature'lar dahil)
        holidays: Tatil günleri

    Returns:
        Prophet: Eğitilmiş model
    """
    print("\n[*] Multivariate Prophet modeli eğitiliyor...")

    model = Prophet(
        # Tatil günleri
        holidays=holidays,

        # Mevsimsellik ayarları
        daily_seasonality=True,   # Gün içi saatlik desenleri yakala
        weekly_seasonality=True,  # Hafta sonu etkisini yakala
        yearly_seasonality=True,  # Mevsimsel desenleri yakala

        # Değişim noktaları (trend değişiklikleri)
        changepoint_prior_scale=0.1,  # Biraz artırıldı, daha esnek trend

        # Bayram etkisi gücü
        holidays_prior_scale=10.0,

        # Mevsimsellik esnekliği
        seasonality_prior_scale=10.0,

        # Tahmin aralığı genişliği
        interval_width=0.95,
    )

    # Türkiye resmi tatillerini ekle
    model.add_country_holidays(country_name='TR')

    # =============================================
    # MULTIVARIATE REGRESSORS - YENİ EKLENDİ!
    # =============================================
    
    regressors = get_prophet_features()
    print(f"   [*] {len(regressors)} regressor ekleniyor...")
    
    # Prior scale değerleri: Yüksek = daha güçlü etki
    prior_scales = {
        'hour': 5.0,
        'is_weekend': 15.0,
        'is_peak_hour': 10.0,
        'is_daytime': 12.0,
        'day_of_week': 3.0,
        # YENİ - Multivariate regressors
        'consumption': 20.0,          # ⭐ Talep - en önemli
        'supply_demand_gap': 15.0,    # ⭐ Arz-talep dengesi
        'renewable_ratio': 12.0,      # Yenilenebilir oranı
        'fossil_ratio': 10.0,         # Fosil yakıt oranı
        'price_lag_24h': 8.0,         # Dünün fiyatı
    }
    
    for reg in regressors:
        prior = prior_scales.get(reg, 5.0)
        model.add_regressor(reg, prior_scale=prior)
        print(f"      + {reg} (prior_scale={prior})")

    print("   [*] Eğitim başlıyor (bu birkaç dakika sürebilir)...")
    
    # Prophet'e fit için sadece gerekli kolonları ver
    train_df = df[['ds', 'y'] + regressors].copy()
    model.fit(train_df)

    print("[+] Model eğitimi tamamlandı!")

    return model


def evaluate_model(model, df):
    """
    Modeli test seti üzerinde değerlendirir

    Args:
        model: Eğitilmiş Prophet modeli
        df: Tüm veri seti

    Returns:
        tuple: (mae, rmse, mape)
    """
    print("\n[*] Model performansı değerlendiriliyor...")

    # Train/test split (son 30 gün test)
    train, test = train_test_split_timeseries(df, test_days=30)

    # Test seti için tahmin yap
    regressors = get_prophet_features()
    test_features = test[['ds'] + regressors].copy()
    forecast = model.predict(test_features)

    # Performans metrikleri
    y_true = test['y'].values
    y_pred = forecast['yhat'].values

    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred)**2))

    # MAPE hesapla (düşük fiyatları filtrele)
    mask = y_true >= 500

    if mask.sum() > 0:
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        print(f"   MAPE hesabında kullanılan: {mask.sum()} / {len(y_true)} kayıt (500+ TRY)")
        print(f"   Filtrelenen düşük fiyat: {len(y_true) - mask.sum()} kayıt (<500 TRY)")
    else:
        mape = 0.0
        print(f"   UYARI: Tüm test verileri 500 TRY altında!")

    print(f"\n[*] Performans Metrikleri (Son 30 Gün):")
    print(f"   MAE  (Ortalama Mutlak Hata): {mae:.2f} TRY")
    print(f"   RMSE (Kök Ort. Kare Hata):   {rmse:.2f} TRY")
    print(f"   MAPE (Ortalama Yüzde Hata):  {mape:.2f}%")

    # Görselleştirme
    plt.figure(figsize=(15, 6))
    plt.plot(test['ds'], y_true, label='Gerçek', color='blue', alpha=0.7)
    plt.plot(test['ds'], y_pred, label='Tahmin', color='red', alpha=0.7)
    plt.fill_between(test['ds'],
                     forecast['yhat_lower'],
                     forecast['yhat_upper'],
                     alpha=0.2, color='red', label='%95 Güven Aralığı')
    plt.xlabel('Tarih')
    plt.ylabel('Fiyat (TRY/MWh)')
    plt.title('Multivariate Prophet Model Performansı - Son 30 Gün')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()

    chart_path = os.path.join(os.path.dirname(__file__), '../../models/test_performance.png')
    plt.savefig(chart_path, dpi=150)
    plt.close()
    print(f"\n[*] Grafik kaydedildi: {chart_path}")

    return mae, rmse, mape


def save_model(model):
    """
    Eğitilmiş modeli JSON formatında kaydeder

    Args:
        model: Eğitilmiş Prophet modeli
    """
    print(f"\n[*] Model kaydediliyor: {MODEL_PATH}")

    from prophet.serialize import model_to_json
    with open(MODEL_PATH, 'w') as f:
        f.write(model_to_json(model))

    print("[+] Model başarıyla kaydedildi!")


def main(end_date=None):
    """
    Ana eğitim fonksiyonu

    Args:
        end_date (str, optional): Bu tarihe KADAR veri kullan (dahil değil!)
                                  Format: 'YYYY-MM-DD'
    
    Returns:
        tuple: (model, mae, rmse, mape)
    """
    print("=" * 60)
    print("EPİAŞ MCP Fiyat Tahmini - MULTIVARIATE Prophet Eğitimi")
    print("=" * 60)

    # 1. Birleştirilmiş veri yükleme (MCP + Consumption + Generation)
    df = load_combined_data(end_date=end_date)

    # 2. Feature engineering
    df = engineer_features(df)
    
    print(f"\n[*] Veri Özeti:")
    print(f"   - Toplam kayıt: {len(df)}")
    print(f"   - Fiyat aralığı: {df['y'].min():.2f} - {df['y'].max():.2f} TRY")
    print(f"   - Ortalama fiyat: {df['y'].mean():.2f} TRY")

    # 3. Tatil günlerini oluştur
    holidays = create_turkish_holidays()

    # 4. Modeli eğit
    model = train_prophet_model(df, holidays)

    # 5. Performansı değerlendir
    mae, rmse, mape = evaluate_model(model, df)

    # 6. Modeli kaydet
    save_model(model)

    print("\n" + "=" * 60)
    print("[+] Eğitim tamamlandı!")
    print("=" * 60)
    print(f"[*] Model Özeti:")
    print(f"   - Tip: Multivariate Prophet")
    print(f"   - Toplam veri: {len(df)} saat")
    print(f"   - Regressor sayısı: {len(get_prophet_features())}")
    print(f"   - Test performansı: MAE={mae:.2f} TRY, MAPE={mape:.2f}%")
    print(f"   - Model dosyası: {MODEL_PATH}")
    print("=" * 60)

    return model, mae, rmse, mape


if __name__ == "__main__":
    import sys
    # Komut satırından end_date parametresi al
    # Kullanım: python train_prophet.py 2025-10-20
    end_date = sys.argv[1] if len(sys.argv) > 1 else None
    main(end_date=end_date)
