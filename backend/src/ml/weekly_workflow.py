#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ MCP Fiyat Tahmini - Haftalık İş Akışı (Ensemble Versiyon)
================================================================

Bu script haftalık döngüyü orkestre eder:
1. Geçen hafta tahmin vs gerçek karşılaştırması
2. Prophet model eğitimi (multivariate)
3. XGBoost residual model eğitimi
4. Bu hafta tahmini (ensemble)
5. JSON export

Her Pazartesi sabah 07:00 TRT'de GitHub Actions tarafından çalıştırılır.

GÜNCELLEME: Prophet + XGBoost Ensemble modeline geçildi!
"""

import sys
import os
from datetime import datetime, timedelta

# Script'in çalıştığı dizin
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)


def get_monday_date(offset_weeks=0):
    """
    Pazartesi tarihini döndürür

    Args:
        offset_weeks (int): Kaç hafta öncesi/sonrası (0 = bu hafta, -1 = geçen hafta)

    Returns:
        str: Pazartesi tarihi (YYYY-MM-DD)
    """
    today = datetime.now()
    days_since_monday = today.weekday()  # Pazartesi = 0
    this_monday = today - timedelta(days=days_since_monday)
    target_monday = this_monday + timedelta(weeks=offset_weeks)
    return target_monday.strftime('%Y-%m-%d')


def get_sunday_date(monday_date):
    """
    Pazartesi tarihinden Pazar tarihini hesaplar

    Args:
        monday_date (str): Pazartesi tarihi (YYYY-MM-DD)

    Returns:
        str: Pazar tarihi (YYYY-MM-DD)
    """
    monday = datetime.strptime(monday_date, '%Y-%m-%d')
    sunday = monday + timedelta(days=6)
    return sunday.strftime('%Y-%m-%d')


def run_weekly_cycle():
    """
    Haftalık döngüyü çalıştırır (Ensemble versiyonu)
    """
    print("\n" + "="*70)
    print("HAFTALİK İŞ AKIŞI BAŞLIYOR (ENSEMBLE MODEL)")
    print("="*70)
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Tarihleri hesapla
    this_week_monday = get_monday_date(0)
    this_week_sunday = get_sunday_date(this_week_monday)

    last_week_monday = get_monday_date(-1)
    last_week_sunday = get_sunday_date(last_week_monday)

    print(f"\n📅 BU HAFTA: {this_week_monday} (Pazartesi) - {this_week_sunday} (Pazar)")
    print(f"📅 GEÇEN HAFTA: {last_week_monday} (Pazartesi) - {last_week_sunday} (Pazar)")

    # =====================================================================
    # ADIM 1: Geçen hafta tahmin vs gerçek karşılaştırması
    # =====================================================================
    print("\n" + "="*70)
    print("ADIM 1: Geçen hafta tahmin vs gerçek karşılaştırması")
    print("="*70)

    try:
        from compare_forecasts import compare_week
        result = compare_week(last_week_monday, last_week_sunday)
        if result:
            print(f"\n✅ Geçen hafta karşılaştırması tamamlandı!")
            print(f"   MAPE: {result['mape']:.2f}%")
            print(f"   MAE: {result['mae']:.2f} TRY")
            print(f"   RMSE: {result['rmse']:.2f} TRY")
        else:
            print("\n⚠️  Geçen hafta karşılaştırması yapılamadı (veri eksik olabilir)")
    except Exception as e:
        print(f"\n⚠️  Geçen hafta karşılaştırması atlandı: {e}")

    # =====================================================================
    # ADIM 2: Multivariate Prophet model eğitimi
    # =====================================================================
    print("\n" + "="*70)
    print("ADIM 2: Multivariate Prophet model eğitimi")
    print("="*70)
    print(f"📚 Eğitim verisi: {this_week_monday} tarihine KADAR (dahil değil)")

    try:
        from train_prophet import main as train_prophet
        model, mae, rmse, mape = train_prophet(end_date=this_week_monday)
        print(f"\n✅ Prophet model eğitimi tamamlandı!")
        print(f"   Test performansı: MAE={mae:.2f} TRY, MAPE={mape:.2f}%")
    except Exception as e:
        print(f"\n❌ Prophet model eğitimi HATA: {e}")
        import traceback
        traceback.print_exc()
        raise e

    # =====================================================================
    # ADIM 3: XGBoost Residual model eğitimi
    # =====================================================================
    print("\n" + "="*70)
    print("ADIM 3: XGBoost Residual model eğitimi")
    print("="*70)

    try:
        from train_xgboost import main as train_xgboost
        xgb_model, features, xgb_mae, xgb_rmse, xgb_mape = train_xgboost()
        print(f"\n✅ XGBoost model eğitimi tamamlandı!")
        print(f"   Ensemble MAPE: {xgb_mape:.2f}%")
    except Exception as e:
        print(f"\n❌ XGBoost model eğitimi HATA: {e}")
        import traceback
        traceback.print_exc()
        raise e

    # =====================================================================
    # ADIM 4: LSTM Deep Learning Model eğitimi (Opsiyonel)
    # =====================================================================
    print("\n" + "="*70)
    print("ADIM 4: LSTM Deep Learning Model eğitimi")
    print("="*70)

    lstm_trained = False
    try:
        from train_lstm import main as train_lstm
        model, scaler_data, metrics = train_lstm()
        lstm_mae, lstm_rmse, lstm_mape = metrics
        lstm_trained = True
        print(f"\n✅ LSTM model eğitimi tamamlandı!")
        print(f"   Test MAPE: {lstm_mape:.2f}%")
    except Exception as e:
        print(f"\n⚠️  LSTM model eğitimi atlandı: {e}")
        print(f"   (TensorFlow yüklü değilse veya GPU yoksa normal)")
        # LSTM opsiyonel - hata olsa bile devam et

    # =====================================================================
    # ADIM 5: Bu hafta tahmini (Ensemble)
    # =====================================================================
    print("\n" + "="*70)
    print("ADIM 5: Bu hafta tahmini (Ensemble Model)")
    print("="*70)
    print(f"🔮 Tahmin aralığı: {this_week_monday} - {this_week_sunday}")

    try:
        from ensemble import EnsembleModel, export_forecasts_json
        from features import load_combined_data, engineer_features
        
        # Veri yükle
        df = load_combined_data()
        df = engineer_features(df)
        
        # Ensemble model
        ensemble = EnsembleModel()
        ensemble.load_models()
        
        # 7 günlük tahmin (bu haftanın Pazartesi'sinden başla)
        forecasts = ensemble.forecast_future(df, days=7, start_date=this_week_monday)
        
        print(f"\n✅ {len(forecasts)} saatlik tahmin üretildi")
        print(f"   Ortalama: {forecasts['predicted_price'].mean():.2f} TRY")
        print(f"   Min: {forecasts['predicted_price'].min():.2f} TRY")
        print(f"   Max: {forecasts['predicted_price'].max():.2f} TRY")

        # Database'e kaydet (opsiyonel)
        try:
            from predict import save_forecast_to_db
            save_forecast_to_db(forecasts, this_week_monday, this_week_sunday)
            print(f"✅ Tahminler database'e kaydedildi")
        except Exception as e:
            print(f"⚠️  Database kayıt atlandı: {e}")

    except Exception as e:
        print(f"\n❌ Tahmin yapma HATA: {e}")
        import traceback
        traceback.print_exc()
        raise e

    # =====================================================================
    # ADIM 6: JSON Export
    # =====================================================================
    print("\n" + "="*70)
    print("ADIM 6: JSON Export (Frontend için)")
    print("="*70)

    try:
        # Ensemble modülü kullanarak export
        export_forecasts_json(ensemble, df, forecasts)
        print(f"✅ JSON export tamamlandı")
    except Exception as e:
        print(f"\n❌ JSON export HATA: {e}")
        import traceback
        traceback.print_exc()

    # =====================================================================
    # ÖZET
    # =====================================================================
    print("\n" + "="*70)
    print("✅ HAFTALİK İŞ AKIŞI TAMAMLANDI!")
    print("="*70)
    print(f"📅 Yeni hafta tahmini hazır: {this_week_monday} - {this_week_sunday}")
    model_type = "Prophet + XGBoost + LSTM Ensemble" if lstm_trained else "Prophet + XGBoost Ensemble"
    print(f"🤖 Model: {model_type}")
    print(f"📊 Geçen hafta performansı kaydedildi")
    print(f"📁 JSON dosyası frontend için güncellendi")
    print("="*70)

    return True


def main():
    """Ana fonksiyon"""
    try:
        success = run_weekly_cycle()
        if success:
            print("\n✅ İşlem başarılı!")
            sys.exit(0)
        else:
            print("\n❌ İşlem başarısız!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
