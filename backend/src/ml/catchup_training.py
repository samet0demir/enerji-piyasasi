#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Eksik Haftalık Eğitimleri Telafi Et
Ocak ayındaki kaçırılmış haftalık model eğitimlerini yapar
"""

import sys
import os
from datetime import datetime, timedelta

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

from compare_forecasts import compare_week

# Eksik haftalar (Pazartesi tarihleri)
MISSED_WEEKS = [
    '2026-01-05',  # 5-11 Ocak
    '2026-01-12',  # 12-18 Ocak
    '2026-01-19',  # 19-25 Ocak
]

def get_sunday_date(monday_str):
    """Pazartesi'den Pazar hesapla"""
    monday = datetime.strptime(monday_str, '%Y-%m-%d')
    sunday = monday + timedelta(days=6)
    return sunday.strftime('%Y-%m-%d')

def catchup_training():
    """Kaçırılmış haftalık eğitimleri yap"""
    print("\n" + "="*70)
    print("KAÇ IRILMIŞ HAFTALIK EĞİTİMLERİ TELAFİ ET")
    print("="*70)

    results = []

    for week_monday in MISSED_WEEKS:
        week_sunday = get_sunday_date(week_monday)

        print(f"\n{'='*70}")
        print(f"HAFTA: {week_monday} - {week_sunday}")
        print(f"{'='*70}")

        try:
            # Geçen hafta tahmin vs gerçek karşılaştırması
            result = compare_week(week_monday, week_sunday)

            if result:
                print(f"\n✅ Karşılaştırma tamamlandı!")
                print(f"   MAPE: {result['mape']:.2f}%")
                print(f"   MAE: {result['mae']:.2f} TRY")
                print(f"   RMSE: {result['rmse']:.2f} TRY")
                results.append({
                    'week': f"{week_monday} - {week_sunday}",
                    'success': True,
                    **result
                })
            else:
                print(f"\n⚠️  Bu hafta için veri eksik")
                results.append({
                    'week': f"{week_monday} - {week_sunday}",
                    'success': False,
                    'reason': 'Veri eksik'
                })

        except Exception as e:
            print(f"\n❌ HATA: {e}")
            results.append({
                'week': f"{week_monday} - {week_sunday}",
                'success': False,
                'reason': str(e)
            })

    # Özet
    print(f"\n{'='*70}")
    print("ÖZET")
    print(f"{'='*70}")

    successful = sum(1 for r in results if r['success'])
    print(f"\nToplam: {len(results)} hafta")
    print(f"Başarılı: {successful} hafta")
    print(f"Başarısız: {len(results) - successful} hafta")

    if successful > 0:
        print("\n✅ TELAFİ EĞİTİMİ TAMAMLANDI!")
    else:
        print("\n⚠️  Hiçbir hafta eğitilemedi")

    return results

if __name__ == "__main__":
    catchup_training()
