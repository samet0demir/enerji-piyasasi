#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Eksik Haftalik Tahminleri Telafi Et
Her hafta icin:
1. O haftaya kadar veri ile Prophet model egit
2. O hafta icin tahmin yap
3. Gercek degerler ile karsilastir
"""

import sys
import os
from datetime import datetime, timedelta

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Telafi edilecek haftalar (Pazartesi tarihleri)
WEEKS_TO_CATCHUP = [
    '2026-01-05',  # 5-11 Ocak
    '2026-01-12',  # 12-18 Ocak
    '2026-01-19',  # 19-25 Ocak
]

def get_sunday_date(monday_str):
    """Pazartesi'den Pazar hesapla"""
    monday = datetime.strptime(monday_str, '%Y-%m-%d')
    sunday = monday + timedelta(days=6)
    return sunday.strftime('%Y-%m-%d')

def catchup_week(week_monday):
    """Bir hafta icin telafi islemi"""
    week_sunday = get_sunday_date(week_monday)

    print(f"\n{'='*70}")
    print(f"HAFTA: {week_monday} - {week_sunday}")
    print(f"{'='*70}")

    try:
        # ADIM 1: Prophet v2 model egit (sadece extreme_low_risk regressor ile)
        print(f"\n[1] Prophet v2 model egitiliyor (veri: {week_monday} oncesi)...")
        from train_prophet_improved import main as train_prophet_v2
        trained_model, mae, rmse, mape = train_prophet_v2(end_date=week_monday)
        print(f"    Egitim tamamlandi: MAE={mae:.2f} TRY, MAPE={mape:.2f}%")

        # ADIM 2: Bu hafta icin tahmin yap (az once egitilen model ile)
        print(f"\n[2] {week_monday} - {week_sunday} icin tahmin yapiliyor...")
        from predict import make_forecast
        forecasts = make_forecast(trained_model, days=7)

        # Sadece bu haftaya ait tahminleri filtrele
        week_start_dt = datetime.strptime(week_monday, '%Y-%m-%d')
        week_end_dt = datetime.strptime(week_sunday, '%Y-%m-%d') + timedelta(days=1)
        forecasts = forecasts[
            (forecasts['ds'] >= week_start_dt) &
            (forecasts['ds'] < week_end_dt)
        ].copy()

        print(f"    {len(forecasts)} saatlik tahmin uretildi")

        # ADIM 3: Database'e kaydet
        print(f"\n[3] Database'e kaydediliyor...")
        from predict import save_forecast_to_db
        save_forecast_to_db(forecasts, week_monday, week_sunday)
        print(f"    Database'e kaydedildi")

        # ADIM 4: Gercek degerler ile karsilastir
        print(f"\n[4] Gercek degerler ile karsilastiriliyor...")
        from compare_forecasts import compare_week
        result = compare_week(week_monday, week_sunday)

        if result:
            print(f"\n    MAPE: {result['mape']:.2f}%")
            print(f"    MAE: {result['mae']:.2f} TRY")
            print(f"    RMSE: {result['rmse']:.2f} TRY")
            return True
        else:
            print(f"\n    Karsilastirma yapilamadi (gercek veri yok olabilir)")
            return True  # Tahmin yapildi, sadece gercek veri yok

    except Exception as e:
        print(f"\n    HATA: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ana fonksiyon"""
    print("\n" + "="*70)
    print("EKSIK HAFTALIK TAHMINLERI TELAFI ET")
    print("="*70)

    results = []

    for week_monday in WEEKS_TO_CATCHUP:
        success = catchup_week(week_monday)
        results.append({
            'week': week_monday,
            'success': success
        })

    # Ozet
    print(f"\n{'='*70}")
    print("OZET")
    print(f"{'='*70}")

    successful = sum(1 for r in results if r['success'])
    print(f"\nToplam: {len(results)} hafta")
    print(f"Basarili: {successful} hafta")
    print(f"Basarisiz: {len(results) - successful} hafta")

    if successful > 0:
        print("\nTELAFI TAMAMLANDI!")
    else:
        print("\nHicbir hafta telafi edilemedi")

    return results

if __name__ == "__main__":
    main()
