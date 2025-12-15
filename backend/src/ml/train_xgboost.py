#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ MCP Fiyat Tahmini - XGBoost Residual Model Eğitimi
=========================================================

Bu script Prophet modelinin yakalayamadığı residual'ları (hataları) 
tahmin etmek için XGBoost modeli eğitir.

Pipeline:
1. Prophet tahminlerini yükle
2. Residual hesapla (gerçek - tahmin)
3. XGBoost ile residual'ları tahmin etmeyi öğren
4. Model'i .joblib olarak kaydet

Ensemble tahmini: final = prophet_pred + xgboost_residual_pred
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

# Feature engineering modülünü import et
from features import (
    load_combined_data, 
    engineer_features, 
    get_xgboost_features,
    train_test_split_timeseries
)

# Prophet modülünden tahmin fonksiyonu
from prophet.serialize import model_from_json

# Model yolları
PROPHET_MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/prophet_model.json')
XGBOOST_MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/xgboost_residual.joblib')


def load_prophet_model():
    """Prophet modelini yükler"""
    print("[*] Prophet modeli yükleniyor...")
    
    with open(PROPHET_MODEL_PATH, 'r') as f:
        model = model_from_json(f.read())
    
    print(f"[+] Prophet modeli yüklendi: {PROPHET_MODEL_PATH}")
    return model


def calculate_prophet_predictions(prophet_model, df):
    """
    Prophet modelinin tahminlerini hesaplar
    
    Args:
        prophet_model: Eğitilmiş Prophet modeli
        df: Feature'lar eklenmiş veri seti
        
    Returns:
        np.array: Prophet tahminleri
    """
    print("[*] Prophet tahminleri hesaplanıyor...")
    
    # Prophet için gerekli kolonlar
    prophet_features = ['ds', 'hour', 'is_weekend', 'is_peak_hour', 'is_daytime', 
                       'day_of_week', 'consumption', 'supply_demand_gap', 
                       'renewable_ratio', 'fossil_ratio', 'price_lag_24h']
    
    # Sadece mevcut kolonları al
    available_features = [col for col in prophet_features if col in df.columns]
    feature_df = df[available_features].copy()
    
    # Prophet tahminleri
    forecast = prophet_model.predict(feature_df)
    
    print(f"[+] {len(forecast)} tahmin hesaplandı")
    
    return forecast['yhat'].values


def calculate_residuals(df, prophet_predictions):
    """
    Residual hesaplar (gerçek - prophet tahmini)
    
    Args:
        df: Gerçek değerleri içeren veri seti
        prophet_predictions: Prophet tahminleri
        
    Returns:
        np.array: Residual'lar
    """
    y_true = df['y'].values
    residuals = y_true - prophet_predictions
    
    print(f"[*] Residual istatistikleri:")
    print(f"   - Min: {residuals.min():.2f}")
    print(f"   - Max: {residuals.max():.2f}")
    print(f"   - Mean: {residuals.mean():.2f}")
    print(f"   - Std: {residuals.std():.2f}")
    
    return residuals


def train_xgboost_model(df, residuals):
    """
    XGBoost modelini residual'ları tahmin etmek için eğitir
    
    Args:
        df: Feature'lar içeren veri seti
        residuals: Prophet residual'ları
        
    Returns:
        xgb.XGBRegressor: Eğitilmiş model
    """
    print("\n[*] XGBoost modeli eğitiliyor...")
    
    # Feature'ları al
    features = get_xgboost_features()
    print(f"   [*] {len(features)} feature kullanılıyor")
    
    # Sadece mevcut kolonları al
    available_features = [f for f in features if f in df.columns]
    print(f"   [*] {len(available_features)} feature mevcut")
    
    X = df[available_features].values
    y = residuals
    
    # Time Series Cross Validation
    print("   [*] Time Series Cross Validation yapılıyor (5 fold)...")
    tscv = TimeSeriesSplit(n_splits=5)
    
    # XGBoost hyperparameters
    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective='reg:squarederror',
        random_state=42,
        n_jobs=-1,
        verbosity=0
    )
    
    # Cross validation ile eğit
    cv_scores = []
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        val_pred = model.predict(X_val)
        val_mae = mean_absolute_error(y_val, val_pred)
        cv_scores.append(val_mae)
        print(f"      Fold {fold+1}: MAE = {val_mae:.2f}")
    
    print(f"\n   [*] CV Ortalama MAE: {np.mean(cv_scores):.2f} (+/- {np.std(cv_scores):.2f})")
    
    # Tüm veri ile final model eğit
    print("   [*] Final model eğitiliyor...")
    model.fit(X, y, verbose=False)
    
    # Feature importance
    print("\n   [*] Önemli Feature'lar (Top 5):")
    importance = pd.DataFrame({
        'feature': available_features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    for i, row in importance.head(5).iterrows():
        print(f"      {row['feature']}: {row['importance']:.4f}")
    
    print("\n[+] XGBoost model eğitimi tamamlandı!")
    
    return model, available_features


def evaluate_ensemble(df, prophet_model, xgboost_model, features, test_days=30):
    """
    Ensemble modelin performansını değerlendirir
    
    Args:
        df: Tüm veri seti
        prophet_model: Prophet modeli
        xgboost_model: XGBoost modeli
        features: XGBoost feature listesi
        test_days: Test süresi (gün)
        
    Returns:
        tuple: (mae, rmse, mape)
    """
    print("\n[*] Ensemble model performansı değerlendiriliyor...")
    
    # Train/test split
    train, test = train_test_split_timeseries(df, test_days=test_days)
    
    # Prophet tahminleri (test seti için)
    prophet_features = ['ds', 'hour', 'is_weekend', 'is_peak_hour', 'is_daytime', 
                       'day_of_week', 'consumption', 'supply_demand_gap', 
                       'renewable_ratio', 'fossil_ratio', 'price_lag_24h']
    available_prophet_features = [col for col in prophet_features if col in test.columns]
    prophet_forecast = prophet_model.predict(test[available_prophet_features])
    prophet_pred = prophet_forecast['yhat'].values
    
    # XGBoost residual tahminleri
    X_test = test[features].values
    xgboost_residual_pred = xgboost_model.predict(X_test)
    
    # Ensemble tahmin
    ensemble_pred = prophet_pred + xgboost_residual_pred
    
    # Gerçek değerler
    y_true = test['y'].values
    
    # Metrikler - Prophet only
    prophet_mae = mean_absolute_error(y_true, prophet_pred)
    prophet_rmse = np.sqrt(mean_squared_error(y_true, prophet_pred))
    
    # Metrikler - Ensemble
    ensemble_mae = mean_absolute_error(y_true, ensemble_pred)
    ensemble_rmse = np.sqrt(mean_squared_error(y_true, ensemble_pred))
    
    # MAPE (500+ TRY için)
    mask = y_true >= 500
    if mask.sum() > 0:
        prophet_mape = np.mean(np.abs((y_true[mask] - prophet_pred[mask]) / y_true[mask])) * 100
        ensemble_mape = np.mean(np.abs((y_true[mask] - ensemble_pred[mask]) / y_true[mask])) * 100
    else:
        prophet_mape = 0
        ensemble_mape = 0
    
    print(f"\n[*] Performans Karşılaştırması (Son {test_days} Gün):")
    print(f"   {'Metrik':<10} {'Prophet':<15} {'Ensemble':<15} {'İyileşme':<10}")
    print(f"   {'-'*50}")
    print(f"   {'MAE':<10} {prophet_mae:<15.2f} {ensemble_mae:<15.2f} {(prophet_mae - ensemble_mae)/prophet_mae*100:+.1f}%")
    print(f"   {'RMSE':<10} {prophet_rmse:<15.2f} {ensemble_rmse:<15.2f} {(prophet_rmse - ensemble_rmse)/prophet_rmse*100:+.1f}%")
    print(f"   {'MAPE':<10} {prophet_mape:<15.2f}% {ensemble_mape:<15.2f}% {(prophet_mape - ensemble_mape)/prophet_mape*100:+.1f}%")
    
    return ensemble_mae, ensemble_rmse, ensemble_mape


def save_model(model, features):
    """
    XGBoost modelini ve feature listesini kaydeder
    
    Args:
        model: Eğitilmiş XGBoost modeli
        features: Kullanılan feature listesi
    """
    print(f"\n[*] Model kaydediliyor: {XGBOOST_MODEL_PATH}")
    
    # Model ve feature'ları birlikte kaydet
    model_data = {
        'model': model,
        'features': features
    }
    
    joblib.dump(model_data, XGBOOST_MODEL_PATH)
    
    print("[+] XGBoost modeli başarıyla kaydedildi!")


def main():
    """Ana eğitim fonksiyonu"""
    print("=" * 60)
    print("EPİAŞ MCP Fiyat Tahmini - XGBoost Residual Eğitimi")
    print("=" * 60)
    
    # 1. Veri yükle ve feature'ları hazırla
    df = load_combined_data()
    df = engineer_features(df)
    
    # 2. Prophet modelini yükle
    prophet_model = load_prophet_model()
    
    # 3. Prophet tahminlerini hesapla
    prophet_predictions = calculate_prophet_predictions(prophet_model, df)
    
    # 4. Residual hesapla
    residuals = calculate_residuals(df, prophet_predictions)
    
    # 5. XGBoost'u residual'ları tahmin etmek için eğit
    xgboost_model, features = train_xgboost_model(df, residuals)
    
    # 6. Ensemble performansını değerlendir
    mae, rmse, mape = evaluate_ensemble(df, prophet_model, xgboost_model, features)
    
    # 7. Modeli kaydet
    save_model(xgboost_model, features)
    
    print("\n" + "=" * 60)
    print("[+] XGBoost eğitimi tamamlandı!")
    print("=" * 60)
    print(f"[*] Model Özeti:")
    print(f"   - Tip: XGBoost Residual Regressor")
    print(f"   - Feature sayısı: {len(features)}")
    print(f"   - Ensemble MAPE: {mape:.2f}%")
    print(f"   - Model dosyası: {XGBOOST_MODEL_PATH}")
    print("=" * 60)
    
    return xgboost_model, features, mae, rmse, mape


if __name__ == "__main__":
    main()
