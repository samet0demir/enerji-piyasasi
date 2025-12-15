#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ MCP Fiyat Tahmini - Ensemble Model
==========================================

Prophet + XGBoost hybrid ensemble model.

Bu modül:
1. Prophet modelini yükler (trend + seasonality)
2. XGBoost modelini yükler (residual prediction)
3. İkisini birleştirerek final tahmin üretir
4. JSON formatında export eder
"""

import pandas as pd
import numpy as np
from prophet.serialize import model_from_json
import joblib
import json
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Feature engineering
from features import (
    load_combined_data,
    engineer_features,
    get_prophet_features,
    get_xgboost_features,
    prepare_future_features
)

# Model yolları
PROPHET_MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/prophet_model.json')
XGBOOST_MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/xgboost_residual.joblib')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../../models')
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), '../../public')
FRONTEND_PUBLIC_DIR = os.path.join(os.path.dirname(__file__), '../../../frontend/public')


class EnsembleModel:
    """Prophet + XGBoost Ensemble Model"""
    
    def __init__(self):
        self.prophet_model = None
        self.xgboost_model = None
        self.xgboost_features = None
        
    def load_models(self):
        """Her iki modeli de yükler"""
        print("[*] Modeller yükleniyor...")
        
        # Prophet
        with open(PROPHET_MODEL_PATH, 'r') as f:
            self.prophet_model = model_from_json(f.read())
        print(f"   [+] Prophet yüklendi: {PROPHET_MODEL_PATH}")
        
        # XGBoost
        xgb_data = joblib.load(XGBOOST_MODEL_PATH)
        self.xgboost_model = xgb_data['model']
        self.xgboost_features = xgb_data['features']
        print(f"   [+] XGBoost yüklendi: {XGBOOST_MODEL_PATH}")
        
        return self
    
    def predict(self, df):
        """
        Ensemble tahmin yapar
        
        Args:
            df: Feature'lar içeren DataFrame
            
        Returns:
            dict: {
                'prophet_pred': np.array,
                'xgboost_pred': np.array,
                'ensemble_pred': np.array,
                'yhat_lower': np.array,
                'yhat_upper': np.array
            }
        """
        # Prophet tahminleri
        prophet_features = ['ds', 'hour', 'is_weekend', 'is_peak_hour', 'is_daytime', 
                           'day_of_week', 'consumption', 'supply_demand_gap', 
                           'renewable_ratio', 'fossil_ratio', 'price_lag_24h']
        
        available_prophet_features = [col for col in prophet_features if col in df.columns]
        prophet_forecast = self.prophet_model.predict(df[available_prophet_features])
        
        prophet_pred = prophet_forecast['yhat'].values
        yhat_lower = prophet_forecast['yhat_lower'].values
        yhat_upper = prophet_forecast['yhat_upper'].values
        
        # XGBoost residual tahminleri
        available_xgb_features = [f for f in self.xgboost_features if f in df.columns]
        xgboost_pred = self.xgboost_model.predict(df[available_xgb_features].values)
        
        # Ensemble
        ensemble_pred = prophet_pred + xgboost_pred
        
        return {
            'prophet_pred': prophet_pred,
            'xgboost_pred': xgboost_pred,
            'ensemble_pred': ensemble_pred,
            'yhat_lower': yhat_lower + xgboost_pred,  # Güven aralığını da kaydır
            'yhat_upper': yhat_upper + xgboost_pred
        }
    
    def forecast_future(self, df, days=7):
        """
        Gelecek için tahmin yapar
        
        Args:
            df: Mevcut veri (feature hesaplaması için)
            days: Kaç gün ileriye tahmin
            
        Returns:
            pd.DataFrame: Gelecek tahminleri
        """
        print(f"\n[*] {days} günlük tahmin yapılıyor...")
        
        # Gelecek tarihler
        last_date = df['ds'].max()
        future_dates = pd.date_range(
            start=last_date + timedelta(hours=1),
            periods=days * 24,
            freq='H'
        )
        
        future_df = pd.DataFrame({'ds': future_dates})
        
        # Feature'ları hazırla
        future_df = prepare_future_features(df, future_df)
        
        # Tahmin yap
        predictions = self.predict(future_df)
        
        # Sonuçları DataFrame'e ekle
        future_df['predicted_price'] = predictions['ensemble_pred']
        future_df['prophet_component'] = predictions['prophet_pred']
        future_df['xgboost_component'] = predictions['xgboost_pred']
        future_df['lower_bound'] = predictions['yhat_lower']
        future_df['upper_bound'] = predictions['yhat_upper']
        
        print(f"[+] {len(future_df)} saatlik tahmin oluşturuldu")
        
        return future_df


def export_forecasts_json(ensemble_model, df, current_week_forecasts, last_week_comparison=None, performance=None, output_path=None):
    """
    Tahminleri frontend için JSON formatında export eder
    
    Args:
        ensemble_model: EnsembleModel instance
        df: Mevcut veri
        current_week_forecasts: Bu haftanın tahminleri
        last_week_comparison: Geçen hafta karşılaştırması
        performance: Performans metrikleri
        output_path: Çıktı dosya yolu
    """
    if output_path is None:
        output_path = os.path.join(PUBLIC_DIR, 'forecasts.json')
    
    print(f"\n[*] JSON export yapılıyor: {output_path}")
    
    # Current week forecasts
    current_week_data = []
    for _, row in current_week_forecasts.iterrows():
        current_week_data.append({
            'datetime': row['ds'].strftime('%Y-%m-%d %H:%M:%S'),
            'predicted': float(row['predicted_price']),
            'prophet': float(row['prophet_component']),
            'xgboost': float(row['xgboost_component']),
            'lower': float(row['lower_bound']),
            'upper': float(row['upper_bound'])
        })
    
    # JSON yapısı
    output = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'model_type': 'Prophet + XGBoost Ensemble',
        'current_week': {
            'start': current_week_forecasts['ds'].min().strftime('%Y-%m-%d'),
            'end': current_week_forecasts['ds'].max().strftime('%Y-%m-%d'),
            'forecasts': current_week_data
        },
        'last_week_comparison': last_week_comparison or [],
        'last_week_performance': performance or {},
        'historical_trend': []  # Weekly performance geçmişi için placeholder
    }
    
    # Kaydet
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"[+] JSON kaydedildi: {output_path}")
    
    # Frontend public klasörüne de kopyala
    frontend_path = os.path.join(FRONTEND_PUBLIC_DIR, 'forecasts.json')
    if os.path.exists(FRONTEND_PUBLIC_DIR):
        with open(frontend_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"[+] Frontend kopyası: {frontend_path}")
    
    return output


def main():
    """Ensemble tahmin ve export"""
    print("=" * 60)
    print("EPİAŞ MCP Fiyat Tahmini - Ensemble Model")
    print("=" * 60)
    
    # 1. Veri yükle
    df = load_combined_data()
    df = engineer_features(df)
    
    # 2. Ensemble model yükle
    ensemble = EnsembleModel()
    ensemble.load_models()
    
    # 3. Gelecek 7 gün için tahmin
    forecasts = ensemble.forecast_future(df, days=7)
    
    # 4. Tahmin özeti
    print("\n[*] Tahmin Özeti:")
    print(f"   - Ortalama: {forecasts['predicted_price'].mean():.2f} TRY")
    print(f"   - Min: {forecasts['predicted_price'].min():.2f} TRY")
    print(f"   - Max: {forecasts['predicted_price'].max():.2f} TRY")
    
    # 5. JSON export
    export_forecasts_json(ensemble, df, forecasts)
    
    print("\n" + "=" * 60)
    print("[+] Ensemble tahmin tamamlandı!")
    print("=" * 60)
    
    return ensemble, forecasts


if __name__ == "__main__":
    main()
