#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ MCP Fiyat Tahmini - Haftalık İş Akışı (v2 - Sadece Prophet v2)
================================================================

Bu script haftalık döngüyü orkestre eder:
1. Geçen hafta tahmin vs gerçek karşılaştırması
2. Prophet v2 model eğitimi (sadece time-based features)
3. Bu hafta tahmini
4. JSON export

Her Pazartesi sabah 07:00 TRT'de GitHub Actions tarafından çalıştırılır.
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
    Haftalık döngüyü çalıştırır (Prophet v2)
    """
    print("\n" + "="*70)
    print("HAFTALIK İŞ AKIŞI BAŞLIYOR (PROPHET V2)")
    print("="*70)
    print(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Tarihleri hesapla
    this_week_monday = get_monday_date(0)
    this_week_sunday = get_sunday_date(this_week_monday)

    last_week_monday = get_monday_date(-1)
    last_week_sunday = get_sunday_date(last_week_monday)

    print(f"\nBU HAFTA: {this_week_monday} (Pazartesi) - {this_week_sunday} (Pazar)")
    print(f"GECEN HAFTA: {last_week_monday} (Pazartesi) - {last_week_sunday} (Pazar)")

    # =====================================================================
    # ADIM 1: Geçen hafta tahmin vs gerçek karşılaştırması
    # =====================================================================
    print("\n" + "="*70)
    print("ADIM 1: Gecen hafta tahmin vs gercek karsilastirmasi")
    print("="*70)

    try:
        from compare_forecasts import compare_week
        result = compare_week(last_week_monday, last_week_sunday)
        if result:
            print(f"\nBasarili! Gecen hafta karsilastirmasi tamamlandi!")
            print(f"   MAPE: {result['mape']:.2f}%")
            print(f"   MAE: {result['mae']:.2f} TRY")
            print(f"   RMSE: {result['rmse']:.2f} TRY")
        else:
            print(f"\nUyari: Gecen hafta karsilastirmasi yapilamadi (veri eksik olabilir)")
    except Exception as e:
        print(f"\nUyari: Gecen hafta karsilastirmasi atlandi: {e}")

    # =====================================================================
    # ADIM 2: Prophet v2 model eğitimi (sadece time-based features)
    # =====================================================================
    print("\n" + "="*70)
    print("ADIM 2: Prophet v2 model egitimi")
    print("="*70)
    print(f"Egitim verisi: {this_week_monday} tarihine KADAR (dahil degil)")

    try:
        from train_prophet_improved import main as train_prophet_v2
        model, mae, rmse, mape = train_prophet_v2()
        print(f"\nBasarili! Prophet v2 model egitimi tamamlandi!")
        print(f"   Test performansi: MAE={mae:.2f} TRY, MAPE={mape:.2f}%")
    except Exception as e:
        print(f"\nHATA: Prophet v2 model egitimi BASARISIZ: {e}")
        import traceback
        traceback.print_exc()
        raise e

    # =====================================================================
    # ADIM 3: Bu hafta tahmini
    # =====================================================================
    print("\n" + "="*70)
    print("ADIM 3: Bu hafta tahmini")
    print("="*70)
    print(f"Tahmin araligi: {this_week_monday} - {this_week_sunday}")

    try:
        from predict import load_model, make_forecast, save_forecast_to_db

        # Prophet v2 modelini yukle
        model = load_model()

        # 7 günlük tahmin
        forecasts = make_forecast(model, days=7)

        print(f"\nBasarili! {len(forecasts)} saatlik tahmin uretildi")
        print(f"   Ortalama: {forecasts['yhat'].mean():.2f} TRY")
        print(f"   Min: {forecasts['yhat'].min():.2f} TRY")
        print(f"   Max: {forecasts['yhat'].max():.2f} TRY")

        # Database'e kaydet
        save_forecast_to_db(forecasts, this_week_monday, this_week_sunday)
        print(f"Basarili! Tahminler database'e kaydedildi")

    except Exception as e:
        print(f"\nHATA: Tahmin yapma BASARISIZ: {e}")
        import traceback
        traceback.print_exc()
        raise e

    # =====================================================================
    # ADIM 4: JSON Export
    # =====================================================================
    print("\n" + "="*70)
    print("ADIM 4: JSON Export (Frontend icin)")
    print("="*70)

    try:
        from export_json import main as export_json
        export_json()
        print(f"Basarili! JSON export tamamlandi")
    except Exception as e:
        print(f"\nHATA: JSON export BASARISIZ: {e}")
        import traceback
        traceback.print_exc()

    # =====================================================================
    # ÖZET
    # =====================================================================
    print("\n" + "="*70)
    print("HAFTALIK IS AKISI TAMAMLANDI!")
    print("="*70)
    print(f"Yeni hafta tahmini hazir: {this_week_monday} - {this_week_sunday}")
    print(f"Model: Prophet v2 (time-based)")
    print(f"Gecen hafta performansi kaydedildi")
    print(f"JSON dosyasi frontend icin guncellendi")
    print("="*70)

    return True


def main():
    """Ana fonksiyon"""
    try:
        success = run_weekly_cycle()
        if success:
            print("\nIslem basarili!")
            sys.exit(0)
        else:
            print("\nIslem basarisiz!")
            sys.exit(1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
