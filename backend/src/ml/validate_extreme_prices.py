#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ekstrem dusuk fiyatlarin dogrulamasi - EPİAŞ verisinde hata var mi?
"""

import pandas as pd
import sqlite3
import os
import sys
from datetime import datetime

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH


def analyze_extreme_prices():
    """Ekstrem dusuk fiyatlari detayli analiz et"""
    print("="*70)
    print("EKSTREM DUSUK FIYAT ANALIZI - Veri Kalitesi Kontrolu")
    print("="*70)

    conn = sqlite3.connect(DB_PATH)

    # Ekstrem dusuk fiyatlari cek (< 100 TRY)
    query = """
        SELECT
            m.date,
            m.hour,
            m.price as mcp_price,
            c.consumption,
            g.solar,
            g.wind,
            g.hydro,
            g.total as total_generation,
            CAST(strftime('%w', m.date) AS INTEGER) as day_of_week
        FROM mcp_data m
        LEFT JOIN consumption_data c ON m.date = c.date
        LEFT JOIN generation_data g ON m.date = g.date
        WHERE m.price < 100
        ORDER BY m.price, m.date
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    df['datetime'] = pd.to_datetime(df['date'])
    df['day_name'] = df['datetime'].dt.day_name()

    print(f"\n[*] Toplam ekstrem dusuk fiyat: {len(df)} kayit")
    print(f"[*] Fiyat araligi: {df['mcp_price'].min():.2f} - {df['mcp_price'].max():.2f} TRY")

    # Fiyat kategorileri
    zero_prices = df[df['mcp_price'] == 0]
    very_low = df[(df['mcp_price'] > 0) & (df['mcp_price'] < 10)]
    low = df[(df['mcp_price'] >= 10) & (df['mcp_price'] < 50)]
    medium_low = df[(df['mcp_price'] >= 50) & (df['mcp_price'] < 100)]

    print(f"\n[*] Kategori dagilimi:")
    print(f"    0 TRY         : {len(zero_prices)} kayit")
    print(f"    0-10 TRY      : {len(very_low)} kayit")
    print(f"    10-50 TRY     : {len(low)} kayit")
    print(f"    50-100 TRY    : {len(medium_low)} kayit")

    # Hafta gunu analizi
    print(f"\n{'='*70}")
    print("HAFTA GUNU DAGILIMI")
    print(f"{'='*70}")
    day_counts = df['day_name'].value_counts()
    for day, count in day_counts.items():
        pct = count / len(df) * 100
        print(f"  {day:10s}: {count:3d} kayit ({pct:5.1f}%)")

    # Saat analizi
    print(f"\n{'='*70}")
    print("SAAT DAGILIMI")
    print(f"{'='*70}")
    df['hour_num'] = df['datetime'].dt.hour
    hour_counts = df.groupby('hour_num').size().sort_index()
    for hour, count in hour_counts.items():
        pct = count / len(df) * 100
        bar = '#' * int(pct / 2)
        print(f"  {hour:02d}:00 | {bar:20s} {count:3d} kayit ({pct:5.1f}%)")

    # Uretim-tuketim dengesi
    print(f"\n{'='*70}")
    print("URETIM-TUKETIM DENGESI ANALIZI")
    print(f"{'='*70}")

    df['generation_consumption_ratio'] = (df['total_generation'] / df['consumption']) * 100

    print(f"\n[*] Arz-Talep Dengesi:")
    print(f"    Ortalama uretim/tuketim orani: {df['generation_consumption_ratio'].mean():.1f}%")
    print(f"    Min: {df['generation_consumption_ratio'].min():.1f}%")
    print(f"    Max: {df['generation_consumption_ratio'].max():.1f}%")

    # Arz fazlasi durumlar (uretim > tuketim)
    oversupply = df[df['total_generation'] > df['consumption']]
    print(f"\n[*] Arz fazlasi durumlar (Uretim > Tuketim):")
    print(f"    {len(oversupply)} / {len(df)} kayit ({len(oversupply)/len(df)*100:.1f}%)")

    if len(oversupply) > 0:
        print(f"    Ortalama fazla uretim: {(oversupply['total_generation'] - oversupply['consumption']).mean():.0f} MWh")

    # Yenilenebilir enerji analizi
    print(f"\n{'='*70}")
    print("YENILENEBILIR ENERJI ANALIZI")
    print(f"{'='*70}")

    df['renewable_pct'] = ((df['solar'] + df['wind']) / df['total_generation']) * 100

    print(f"\n[*] Yenilenebilir enerji payi (Gunes + Ruzgar):")
    print(f"    Ortalama: {df['renewable_pct'].mean():.1f}%")
    print(f"    Min: {df['renewable_pct'].min():.1f}%")
    print(f"    Max: {df['renewable_pct'].max():.1f}%")

    # En dusuk 10 fiyat detayli
    print(f"\n{'='*70}")
    print("EN DUSUK 10 FIYAT DETAYLI ANALIZ")
    print(f"{'='*70}")

    top10 = df.nsmallest(10, 'mcp_price')

    print(f"\n{'Tarih':20s} {'Gun':10s} {'Saat':5s} {'Fiyat':8s} {'Tuketim':10s} {'Uretim':10s} {'Solar%':8s}")
    print("-" * 90)

    for _, row in top10.iterrows():
        dt = row['datetime']
        solar_pct = (row['solar'] / row['total_generation'] * 100) if row['total_generation'] > 0 else 0
        print(f"{dt.strftime('%Y-%m-%d %H:%M'):20s} "
              f"{row['day_name']:10s} "
              f"{dt.hour:02d}:00 "
              f"{row['mcp_price']:7.2f} "
              f"{row['consumption']:9.0f} "
              f"{row['total_generation']:9.0f} "
              f"{solar_pct:7.1f}%")

    # Patern tespiti
    print(f"\n{'='*70}")
    print("PATERN TESPITI - DUSUK FIYATLARIN ORTAK OZELLIKLERI")
    print(f"{'='*70}")

    sunday_count = len(df[df['day_name'] == 'Sunday'])
    midday_count = len(df[(df['hour_num'] >= 10) & (df['hour_num'] <= 14)])
    oversupply_count = len(df[df['total_generation'] > df['consumption']])
    high_solar_count = len(df[df['renewable_pct'] > 50])

    print(f"\n[*] Ortak ozellikler:")
    print(f"    Pazar gunu        : {sunday_count}/{len(df)} ({sunday_count/len(df)*100:.1f}%)")
    print(f"    Ogle saatleri (10-14): {midday_count}/{len(df)} ({midday_count/len(df)*100:.1f}%)")
    print(f"    Arz fazlasi       : {oversupply_count}/{len(df)} ({oversupply_count/len(df)*100:.1f}%)")
    print(f"    Yuksek solar (>50%): {high_solar_count}/{len(df)} ({high_solar_count/len(df)*100:.1f}%)")

    # Kombinasyon analizi
    perfect_storm = df[
        (df['day_name'] == 'Sunday') &
        (df['hour_num'] >= 10) &
        (df['hour_num'] <= 14) &
        (df['total_generation'] > df['consumption'])
    ]

    print(f"\n[*] 'Perfect Storm' (Pazar + Ogle + Arz fazlasi):")
    print(f"    {len(perfect_storm)}/{len(df)} kayit ({len(perfect_storm)/len(df)*100:.1f}%)")

    # Sonuc
    print(f"\n{'='*70}")
    print("DEGERLENDIRME")
    print(f"{'='*70}")

    # Pazar ve ogle saati kontrolu
    if sunday_count / len(df) > 0.8 and midday_count / len(df) > 0.8:
        print("\n[+] VERI DOGRU GORUNUYOR:")
        print("    - Dusuk fiyatlar cogunlukla Pazar gunleri")
        print("    - Ogle saatlerinde yogunlasmis (gunes enerjisi zirve)")
        print("    - Arz fazlasi durumlari ile uyumlu")
        print("    - Bu GERCEK piyasa dinamigidir, hata degil!")

        print("\n[*] ACIKLAMA:")
        print("    Pazar gunleri:")
        print("    - Sanayi uretimi dusuk (fabrikalar kapali)")
        print("    - Tuketim minimum seviyede")
        print("    - Gunes enerjisi uretimine devam ediyor")
        print("    - Sonuc: Arz > Talep -> Fiyat 0'a dusuyor")

        print("\n[*] ENERJI SEKTORUNDE BILINEN OLAY:")
        print("    - 'Negatif fiyat' veya 'sifir fiyat' olaylari")
        print("    - Avrupa'da da gorulur (Almanya, Ispanya)")
        print("    - Yenilenebilir enerjinin artisiyla normal")
    else:
        print("\n[!] VERI ANORMAL GORUNUYOR:")
        print("    - Dusuk fiyatlar belirli paterne uymamis")
        print("    - EPİAŞ verisinde hata olabilir")
        print("    - Manuel kontrol onerilir")

    print("="*70)

    return df

if __name__ == "__main__":
    extreme_df = analyze_extreme_prices()
