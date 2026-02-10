#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backtesting Script - Tüm geçmiş haftalar için MAPE hesaplama
"""

import sqlite3
import os
from datetime import datetime, timedelta
import sys

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH

# compare_forecasts modülünü import et
from compare_forecasts import compare_week

def get_all_forecast_weeks():
    """Forecast history'deki tüm haftaları döndürür"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        SELECT DISTINCT week_start 
        FROM forecast_history 
        ORDER BY week_start
    ''')
    weeks = [row[0] for row in cur.fetchall()]
    conn.close()
    return weeks

def calculate_week_end(week_start):
    """Pazartesi tarihinden Pazar tarihini hesaplar"""
    monday = datetime.strptime(week_start, '%Y-%m-%d')
    sunday = monday + timedelta(days=6)
    return sunday.strftime('%Y-%m-%d')

def run_backtesting():
    """Tüm geçmiş haftalar için MAPE hesaplar"""
    print("=" * 70)
    print("BACKTESTING - TÜM HAFTALAR İÇİN MAPE HESAPLAMA")
    print("=" * 70)
    
    # Tüm haftaları al
    weeks = get_all_forecast_weeks()
    print(f"\n[*] Toplam {len(weeks)} hafta bulundu")
    print(f"    İlk hafta: {weeks[0]}")
    print(f"    Son hafta: {weeks[-1]}")
    
    results = []
    
    for week_start in weeks:
        week_end = calculate_week_end(week_start)
        
        # Bugünden sonraki haftaları atla (henüz gerçek veri yok)
        if datetime.strptime(week_end, '%Y-%m-%d') > datetime.now():
            print(f"\n[!] {week_start} atlandı (henüz gerçek veri yok)")
            continue
        
        # Karşılaştırmayı çalıştır
        result = compare_week(week_start, week_end)
        
        if result:
            results.append({
                'week_start': week_start,
                'week_end': week_end,
                **result
            })
    
    # Özet
    print("\n" + "=" * 70)
    print("BACKTESTING SONUÇLARI")
    print("=" * 70)
    print(f"\n{'Hafta':<15} {'MAPE':<10} {'MAE':<12} {'RMSE':<12} {'Tahmin':<10}")
    print("-" * 60)
    
    for r in results:
        print(f"{r['week_start']:<15} {r['mape']:.2f}%{'':<5} {r['mae']:.2f} TRY{'':<3} {r['rmse']:.2f} TRY{'':<3} {r['total_predictions']:<10}")
    
    if results:
        avg_mape = sum(r['mape'] for r in results) / len(results)
        avg_mae = sum(r['mae'] for r in results) / len(results)
        print("-" * 60)
        print(f"{'ORTALAMA':<15} {avg_mape:.2f}%{'':<5} {avg_mae:.2f} TRY")
    
    print("\n[+] Backtesting tamamlandı!")
    return results

if __name__ == "__main__":
    run_backtesting()
