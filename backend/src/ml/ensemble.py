#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ MCP Fiyat Tahmini - Ensemble Model (3 Model)
====================================================

Prophet + XGBoost + LSTM hybrid ensemble model.

Bu modül:
1. Prophet modelini yükler (trend + seasonality)
2. XGBoost modelini yükler (residual prediction)
3. LSTM modelini yükler (sequence-based prediction)
4. Üçünü birleştirerek final tahmin üretir
5. JSON formatında export eder
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

# TensorFlow import
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
try:
    from tensorflow import keras
    LSTM_AVAILABLE = True
except ImportError:
    LSTM_AVAILABLE = False
    print("[!] TensorFlow yok, LSTM devre dışı")

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
LSTM_MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/lstm_model.keras')
LSTM_SCALER_PATH = os.path.join(os.path.dirname(__file__), '../../models/lstm_scaler.joblib')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../../models')
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), '../../public')
FRONTEND_PUBLIC_DIR = os.path.join(os.path.dirname(__file__), '../../../frontend/public')

# Default ağırlıklar (ilk çalıştırmada kullanılır)
DEFAULT_WEIGHTS = {
    'prophet': 0.4,
    'xgboost': 0.35,
    'lstm': 0.25
}

# Ağırlık dosyası
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), '../../models/ensemble_weights.json')


class EnsembleModel:
    """Prophet + XGBoost + LSTM Ensemble Model (3 Model)"""
    
    def __init__(self):
        self.prophet_model = None
        self.xgboost_model = None
        self.xgboost_features = None
        self.lstm_model = None
        self.lstm_scaler = None
        self.use_lstm = False
        self.weights = DEFAULT_WEIGHTS.copy()
    
    def calculate_weights_from_errors(self, mae_prophet, mae_xgboost, mae_lstm=None):
        """
        Inverse Error Weighting - Hatası düşük olan model daha yüksek ağırlık alır
        
        Args:
            mae_prophet: Prophet MAE
            mae_xgboost: XGBoost (ensemble) MAE  
            mae_lstm: LSTM MAE (opsiyonel)
        
        Returns:
            dict: Hesaplanan ağırlıklar
        """
        if mae_lstm is not None and mae_lstm > 0:
            # 3 model
            inv_errors = [1/mae_prophet, 1/mae_xgboost, 1/mae_lstm]
            total = sum(inv_errors)
            self.weights = {
                'prophet': inv_errors[0] / total,
                'xgboost': inv_errors[1] / total,
                'lstm': inv_errors[2] / total
            }
        else:
            # 2 model
            inv_errors = [1/mae_prophet, 1/mae_xgboost]
            total = sum(inv_errors)
            self.weights = {
                'prophet': inv_errors[0] / total,
                'xgboost': inv_errors[1] / total,
                'lstm': 0
            }
        
        # Ağırlıkları kaydet
        self._save_weights()
        
        print(f"   [*] Yeni ağırlıklar hesaplandı (Inverse Error Weighting):")
        print(f"       Prophet: {self.weights['prophet']:.1%}")
        print(f"       XGBoost: {self.weights['xgboost']:.1%}")
        print(f"       LSTM:    {self.weights['lstm']:.1%}")
        
        return self.weights
    
    def _save_weights(self):
        """Ağırlıkları dosyaya kaydeder"""
        import json
        with open(WEIGHTS_PATH, 'w') as f:
            json.dump(self.weights, f, indent=2)
    
    def _load_weights(self):
        """Kaydedilmiş ağırlıkları yükler"""
        import json
        if os.path.exists(WEIGHTS_PATH):
            with open(WEIGHTS_PATH, 'r') as f:
                self.weights = json.load(f)
                print(f"   [*] Ağırlıklar yüklendi: Prophet={self.weights['prophet']:.1%}, XGBoost={self.weights['xgboost']:.1%}, LSTM={self.weights['lstm']:.1%}")
        else:
            print(f"   [!] Ağırlık dosyası yok, default kullanılıyor")
        
    def load_models(self):
        """Tüm modelleri yükler"""
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
        
        # LSTM (opsiyonel)
        if LSTM_AVAILABLE and os.path.exists(LSTM_MODEL_PATH) and os.path.exists(LSTM_SCALER_PATH):
            try:
                self.lstm_model = keras.models.load_model(LSTM_MODEL_PATH)
                self.lstm_scaler = joblib.load(LSTM_SCALER_PATH)
                self.use_lstm = True
                print(f"   [+] LSTM yüklendi: {LSTM_MODEL_PATH}")
            except Exception as e:
                print(f"   [!] LSTM yüklenemedi: {e}")
                self.use_lstm = False
        else:
            print(f"   [!] LSTM model bulunamadı, 2 model ile devam edilecek")
            self.use_lstm = False
        
        # Kaydedilmiş ağırlıkları yükle
        self._load_weights()
        
        model_count = 3 if self.use_lstm else 2
        print(f"   [*] Toplam {model_count} model aktif")
        
        return self
    
    def _predict_lstm(self, df):
        """LSTM ile tahmin yapar"""
        if not self.use_lstm:
            return np.zeros(len(df))
        
        features = self.lstm_scaler['features']
        scaler_X = self.lstm_scaler['scaler_X']
        scaler_y = self.lstm_scaler['scaler_y']
        seq_length = self.lstm_scaler['sequence_length']
        
        available_features = [f for f in features if f in df.columns]
        if len(available_features) != len(features):
            print(f"   [!] LSTM: Eksik feature'lar, atlanıyor")
            return np.zeros(len(df))
        
        X = df[available_features].values
        X_scaled = scaler_X.transform(X)
        
        # Sequence oluştur ve tahmin yap
        predictions = []
        for i in range(len(X_scaled)):
            if i < seq_length:
                # İlk seq_length satır için yeterli geçmiş yok
                predictions.append(0)
            else:
                seq = X_scaled[i-seq_length:i].reshape(1, seq_length, -1)
                pred_scaled = self.lstm_model.predict(seq, verbose=0)
                pred = scaler_y.inverse_transform(pred_scaled).flatten()[0]
                predictions.append(pred)
        
        return np.array(predictions)
    
    def predict(self, df, mode='weighted'):
        """
        Ensemble tahmin yapar
        
        Args:
            df: Feature'lar içeren DataFrame
            mode: 'weighted' | 'residual' | 'individual'
                - weighted: Ağırlıklı ortalama
                - residual: Prophet + XGBoost residual + LSTM residual
                - individual: Tüm modelleri ayrı döndür
            
        Returns:
            dict: Tahminler
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
        
        # LSTM tahminleri
        lstm_pred = self._predict_lstm(df)
        
        # Ensemble stratejisi - Inverse Error Weighting
        if mode == 'residual':
            # Prophet base + corrections
            ensemble_pred = prophet_pred + xgboost_pred + lstm_pred * 0.5
        else:
            # Ağırlıklı ortalama (LSTM kullanılıyorsa)
            if self.use_lstm and np.any(lstm_pred != 0):
                w = self.weights
                ensemble_pred = (
                    w['prophet'] * prophet_pred + 
                    w['xgboost'] * (prophet_pred + xgboost_pred) + 
                    w['lstm'] * lstm_pred
                )
            else:
                # 2 model: Prophet + XGBoost residual
                ensemble_pred = prophet_pred + xgboost_pred
        
        return {
            'prophet_pred': prophet_pred,
            'xgboost_pred': xgboost_pred,
            'lstm_pred': lstm_pred,
            'ensemble_pred': ensemble_pred,
            'yhat_lower': yhat_lower + xgboost_pred * 0.5,
            'yhat_upper': yhat_upper + xgboost_pred * 0.5,
            'models_used': 3 if self.use_lstm else 2
        }
    
    def forecast_future(self, df, days=7, start_date=None):
        """
        Gelecek için tahmin yapar
        
        Args:
            df: Feature'lar içeren DataFrame
            days: Tahmin günü sayısı
            start_date: Başlangıç tarihi (opsiyonel, YYYY-MM-DD formatında)
                        Verilmezse verinin son tarihinden itibaren başlar
        """
        print(f"\n[*] {days} günlük tahmin yapılıyor...")
        
        # Gelecek tarihler
        if start_date:
            # Belirtilen tarihten başla (00:00)
            from datetime import datetime as dt
            start = dt.strptime(start_date, '%Y-%m-%d')
            future_dates = pd.date_range(
                start=start,
                periods=days * 24,
                freq='H'
            )
            print(f"   [*] Başlangıç: {start_date} (hafta başı)")
        else:
            # Verinin son tarihinden itibaren
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
        future_df['lstm_component'] = predictions['lstm_pred']
        future_df['lower_bound'] = predictions['yhat_lower']
        future_df['upper_bound'] = predictions['yhat_upper']
        
        model_count = predictions['models_used']
        print(f"[+] {len(future_df)} saatlik tahmin oluşturuldu ({model_count} model)")
        
        return future_df


def export_forecasts_json(ensemble_model, df, current_week_forecasts, last_week_comparison=None, performance=None, output_path=None):
    """Tahminleri frontend için JSON formatında export eder"""
    if output_path is None:
        output_path = os.path.join(PUBLIC_DIR, 'forecasts.json')
    
    print(f"\n[*] JSON export yapılıyor: {output_path}")
    
    # Current week forecasts
    current_week_data = []
    for _, row in current_week_forecasts.iterrows():
        forecast_item = {
            'datetime': row['ds'].strftime('%Y-%m-%d %H:%M:%S'),
            'predicted': float(row['predicted_price']),
            'prophet': float(row['prophet_component']),
            'xgboost': float(row['xgboost_component']),
            'lower': float(row['lower_bound']),
            'upper': float(row['upper_bound'])
        }
        # LSTM varsa ekle (0 değeri de dahil - dashboard grafiği için gerekli)
        if 'lstm_component' in row:
            forecast_item['lstm'] = float(row['lstm_component'])
        current_week_data.append(forecast_item)
    
    # Model tipi
    model_type = 'Prophet + XGBoost + LSTM Ensemble' if ensemble_model.use_lstm else 'Prophet + XGBoost Ensemble'
    
    # JSON yapısı
    output = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'model_type': model_type,
        'models_count': 3 if ensemble_model.use_lstm else 2,
        'current_week': {
            'start': current_week_forecasts['ds'].min().strftime('%Y-%m-%d'),
            'end': current_week_forecasts['ds'].max().strftime('%Y-%m-%d'),
            'forecasts': current_week_data
        },
        'last_week_comparison': last_week_comparison or [],
        'last_week_performance': performance or {},
        'historical_trend': []
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
    print("EPİAŞ MCP Fiyat Tahmini - Ensemble Model (3 Model)")
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
