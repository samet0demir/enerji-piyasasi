#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ MCP Fiyat Tahmini - LSTM Deep Learning Model
====================================================

Bu script:
1. Sequence formatında veri hazırlar
2. LSTM (Long Short-Term Memory) modeli eğitir
3. Model'i Keras formatında kaydeder (.keras)
4. Ensemble'a dahil edilmek üzere residual tahmin yapar

LSTM Avantajları:
- Uzun vadeli bağımlılıkları öğrenir
- Sequence-to-sequence tahmin
- Spike'ları daha iyi yakalayabilir
"""

import numpy as np
import pandas as pd
import os
import warnings
warnings.filterwarnings('ignore')

# TensorFlow imports
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TF warnings
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib

# Feature engineering modülünü import et
from features import (
    load_combined_data,
    engineer_features,
    get_xgboost_features,
    train_test_split_timeseries
)

# Model yolları
LSTM_MODEL_PATH = os.path.join(os.path.dirname(__file__), '../../models/lstm_model.keras')
SCALER_PATH = os.path.join(os.path.dirname(__file__), '../../models/lstm_scaler.joblib')

# Hyperparameters
SEQUENCE_LENGTH = 24  # Son 24 saat (1 gün)
EPOCHS = 50
BATCH_SIZE = 32
LSTM_UNITS = 64


def create_sequences(data, target, seq_length):
    """
    LSTM için sequence formatında veri oluşturur
    
    Args:
        data: Feature array (n_samples, n_features)
        target: Target array (n_samples,)
        seq_length: Sequence uzunluğu
        
    Returns:
        X: (n_samples - seq_length, seq_length, n_features)
        y: (n_samples - seq_length,)
    """
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:(i + seq_length)])
        y.append(target[i + seq_length])
    return np.array(X), np.array(y)


def build_lstm_model(input_shape):
    """
    LSTM model mimarisini oluşturur
    
    Args:
        input_shape: (sequence_length, n_features)
        
    Returns:
        Compiled Keras model
    """
    print(f"[*] LSTM model oluşturuluyor: input_shape={input_shape}")
    
    model = Sequential([
        # İlk LSTM katmanı
        LSTM(LSTM_UNITS, return_sequences=True, input_shape=input_shape),
        BatchNormalization(),
        Dropout(0.2),
        
        # İkinci LSTM katmanı
        LSTM(LSTM_UNITS // 2, return_sequences=False),
        BatchNormalization(),
        Dropout(0.2),
        
        # Dense katmanlar
        Dense(32, activation='relu'),
        Dropout(0.1),
        Dense(16, activation='relu'),
        
        # Çıkış katmanı
        Dense(1)
    ])
    
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='mse',
        metrics=['mae']
    )
    
    print(f"[+] Model parametreleri: {model.count_params():,}")
    return model


def train_lstm_model(df, test_days=30):
    """
    LSTM modelini eğitir
    
    Args:
        df: Feature'lar eklenmiş veri seti
        test_days: Test için ayrılacak gün sayısı
        
    Returns:
        model: Eğitilmiş LSTM modeli
        scaler: Kullanılan scaler
        history: Eğitim geçmişi
    """
    print("\n[*] LSTM model eğitimi başlıyor...")
    
    # Feature'ları seç
    feature_cols = get_xgboost_features()
    available_features = [f for f in feature_cols if f in df.columns]
    
    print(f"   [*] {len(available_features)} feature kullanılıyor")
    
    # Train/test split
    train, test = train_test_split_timeseries(df, test_days=test_days)
    
    # Feature ve target ayır
    X_train = train[available_features].values
    y_train = train['y'].values
    X_test = test[available_features].values
    y_test = test['y'].values
    
    # Scaling
    print("   [*] Veri normalizasyonu yapılıyor...")
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    
    X_train_scaled = scaler_X.fit_transform(X_train)
    X_test_scaled = scaler_X.transform(X_test)
    y_train_scaled = scaler_y.fit_transform(y_train.reshape(-1, 1)).flatten()
    y_test_scaled = scaler_y.transform(y_test.reshape(-1, 1)).flatten()
    
    # Sequence oluştur
    print(f"   [*] Sequence'lar oluşturuluyor (length={SEQUENCE_LENGTH})...")
    X_train_seq, y_train_seq = create_sequences(X_train_scaled, y_train_scaled, SEQUENCE_LENGTH)
    X_test_seq, y_test_seq = create_sequences(X_test_scaled, y_test_scaled, SEQUENCE_LENGTH)
    
    print(f"   [+] Train: {X_train_seq.shape}, Test: {X_test_seq.shape}")
    
    # Model oluştur
    input_shape = (SEQUENCE_LENGTH, len(available_features))
    model = build_lstm_model(input_shape)
    
    # Callbacks
    callbacks = [
        EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=0.0001,
            verbose=1
        )
    ]
    
    # Eğitim
    print(f"\n   [*] Eğitim başlıyor (epochs={EPOCHS}, batch_size={BATCH_SIZE})...")
    history = model.fit(
        X_train_seq, y_train_seq,
        validation_data=(X_test_seq, y_test_seq),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1
    )
    
    # Performans değerlendirme
    print("\n[*] Model performansı değerlendiriliyor...")
    y_pred_scaled = model.predict(X_test_seq, verbose=0)
    y_pred = scaler_y.inverse_transform(y_pred_scaled).flatten()
    y_true = scaler_y.inverse_transform(y_test_seq.reshape(-1, 1)).flatten()
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    
    # MAPE (500+ TRY için)
    mask = y_true >= 500
    if mask.sum() > 0:
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    else:
        mape = 0
    
    print(f"\n[*] LSTM Performans Metrikleri:")
    print(f"   MAE:  {mae:.2f} TRY")
    print(f"   RMSE: {rmse:.2f} TRY")
    print(f"   MAPE: {mape:.2f}%")
    
    # Scaler'ları kaydet
    scaler_data = {
        'scaler_X': scaler_X,
        'scaler_y': scaler_y,
        'features': available_features,
        'sequence_length': SEQUENCE_LENGTH
    }
    
    return model, scaler_data, history, (mae, rmse, mape)


def save_model(model, scaler_data):
    """Model ve scaler'ları kaydeder"""
    print(f"\n[*] Model kaydediliyor: {LSTM_MODEL_PATH}")
    model.save(LSTM_MODEL_PATH)
    
    print(f"[*] Scaler kaydediliyor: {SCALER_PATH}")
    joblib.dump(scaler_data, SCALER_PATH)
    
    print("[+] LSTM modeli başarıyla kaydedildi!")


def load_lstm_model():
    """Kaydedilmiş LSTM modelini yükler"""
    model = keras.models.load_model(LSTM_MODEL_PATH)
    scaler_data = joblib.load(SCALER_PATH)
    return model, scaler_data


def predict_with_lstm(df, model, scaler_data):
    """
    LSTM ile tahmin yapar
    
    Args:
        df: Feature'lar eklenmiş veri (son SEQUENCE_LENGTH satır gerekli)
        model: LSTM modeli
        scaler_data: Scaler bilgileri
        
    Returns:
        predictions: Tahminler
    """
    features = scaler_data['features']
    scaler_X = scaler_data['scaler_X']
    scaler_y = scaler_data['scaler_y']
    seq_length = scaler_data['sequence_length']
    
    # Feature'ları al ve scale et
    X = df[features].values
    X_scaled = scaler_X.transform(X)
    
    # Son seq_length satırdan sequence oluştur
    predictions = []
    for i in range(seq_length, len(X_scaled)):
        seq = X_scaled[i-seq_length:i].reshape(1, seq_length, -1)
        pred_scaled = model.predict(seq, verbose=0)
        pred = scaler_y.inverse_transform(pred_scaled).flatten()[0]
        predictions.append(pred)
    
    return np.array(predictions)


def main():
    """Ana eğitim fonksiyonu"""
    print("=" * 60)
    print("EPİAŞ MCP Fiyat Tahmini - LSTM Model Eğitimi")
    print("=" * 60)
    
    # 1. Veri yükle
    df = load_combined_data()
    df = engineer_features(df)
    
    print(f"\n[*] Veri Özeti:")
    print(f"   - Toplam kayıt: {len(df)}")
    print(f"   - Fiyat aralığı: {df['y'].min():.2f} - {df['y'].max():.2f} TRY")
    
    # 2. Model eğit
    model, scaler_data, history, metrics = train_lstm_model(df)
    mae, rmse, mape = metrics
    
    # 3. Modeli kaydet
    save_model(model, scaler_data)
    
    print("\n" + "=" * 60)
    print("[+] LSTM Eğitimi Tamamlandı!")
    print("=" * 60)
    print(f"[*] Model Özeti:")
    print(f"   - Tip: LSTM (Deep Learning)")
    print(f"   - Sequence length: {SEQUENCE_LENGTH}")
    print(f"   - LSTM units: {LSTM_UNITS}")
    print(f"   - Test MAPE: {mape:.2f}%")
    print(f"   - Model dosyası: {LSTM_MODEL_PATH}")
    print("=" * 60)
    
    return model, scaler_data, metrics


if __name__ == "__main__":
    main()
