#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EPİAŞ API Dogrulama - Veritabanindaki degerler API ile ayni mi?
EPİAş API Dogrulama - Veritabanindaki degerler API ile ayni mi?
"""

import requests
import sqlite3
import os
import time
import sys
from datetime import datetime

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH

# EPİAŞ credentials (environment variables'dan al)
EPIAS_USERNAME = os.getenv('EPIAS_USERNAME', 'your_username')
EPIAS_PASSWORD = os.getenv('EPIAS_PASSWORD', 'your_password')

def get_tgt():
    """TGT al"""
    url = 'https://giris.epias.com.tr/cas/v1/tickets'
    data = f'username={EPIAS_USERNAME}&password={EPIAS_PASSWORD}'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        response = requests.post(url, data=data, headers=headers)
        location = response.headers.get('location')
        if not location:
            raise Exception('TGT alinamadi: location header yok')

        tgt = location.split('/')[-1]
        return tgt
    except Exception as e:
        print(f"[!] TGT hatasi: {e}")
        return None

def fetch_mcp_from_api(date_str, tgt):
    """Belirli bir tarihteki MCP fiyatini API'den cek"""
    # date_str: "2024-03-31T12:00:00+03:00"

    date_only = date_str.split('T')[0]
    start_date = f"{date_only}T00:00:00+03:00"
    end_date = f"{date_only}T23:59:59+03:00"

    url = 'https://seffaflik.epias.com.tr/electricity-service/v1/markets/dam/data/mcp'
    payload = {
        'startDate': start_date,
        'endDate': end_date
    }
    headers = {
        'Content-Type': 'application/json',
        'TGT': tgt
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            return None

        data = response.json()
        items = data.get('items', [])

        # Ayni saati bul
        target_hour = date_str.split('T')[1][:5] if 'T' in date_str else None

        for item in items:
            item_date = item.get('date', '')
            if item_date == date_str or (target_hour and target_hour in item_date):
                return item.get('price')

        return None
    except Exception as e:
        print(f"[!] API hatasi: {e}")
        return None

def verify_suspicious_prices():
    """Sifir ve dusuk fiyatlari dogrula"""
    print("="*80)
    print("EPİAŞ VERİ DOGRULAMA - API vs Veritabani Karsilastirmasi")
    print("="*80)

    # TGT al
    print("\n[*] EPİAŞ'a baglaniliyor (TGT aliniyor)...")
    tgt = get_tgt()

    if not tgt:
        print("\n[!] HATA: EPİAŞ'a baglanamadi!")
        print("    Lutfen EPIAS_USERNAME ve EPIAS_PASSWORD environment variable'larini ayarlayin.")
        print("\n    Windows PowerShell:")
        print('    $env:EPIAS_USERNAME="kullanici_adi"')
        print('    $env:EPIAS_PASSWORD="sifre"')
        print("\n    Sonra scripti tekrar calistirin:")
        print("    .\\venv\\Scripts\\python.exe src\\ml\\verify_epias_api.py")
        return

    print(f"[+] TGT alindi: {tgt[:10]}...")

    # Veritabanindan suphelileri cek
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, hour, price
        FROM mcp_data
        WHERE price < 100
        ORDER BY price ASC
        LIMIT 20
    """)

    records = cursor.fetchall()
    conn.close()

    print(f"\n[*] {len(records)} suppheli kayit dogrulanacak...")
    print("[*] Her kayit icin API cagrisi yapiliyor (yaklasik 30 saniye)...\n")

    results = []

    for idx, (date, hour, db_price) in enumerate(records, 1):
        print(f"[{idx}/{len(records)}] Kontrol: {date} ({db_price:.2f} TRY)... ", end='', flush=True)

        api_price = fetch_mcp_from_api(date, tgt)

        if api_price is None:
            print("HATA (API cevap vermedi)")
            results.append({
                'date': date,
                'db_price': db_price,
                'api_price': None,
                'match': False,
                'error': True
            })
        else:
            match = abs(api_price - db_price) < 0.01
            if match:
                print(f"ESLIYOR ({api_price:.2f} TRY)")
            else:
                print(f"FARKLI! API: {api_price:.2f} TRY")

            results.append({
                'date': date,
                'db_price': db_price,
                'api_price': api_price,
                'match': match,
                'error': False
            })

        # Rate limiting
        time.sleep(1)

    # Rapor
    print("\n" + "="*80)
    print("DOGRULAMA RAPORU")
    print("="*80)

    print(f"\n{'Tarih':27s} {'DB Fiyat':12s} {'API Fiyat':12s} {'Durum':20s}")
    print("-"*80)

    match_count = 0
    mismatch_count = 0
    error_count = 0

    for r in results:
        date_str = r['date'][:19]
        db_price_str = f"{r['db_price']:.2f} TRY"
        api_price_str = f"{r['api_price']:.2f} TRY" if r['api_price'] is not None else "HATA"

        if r['error']:
            status = "HATA (API cevap yok)"
            error_count += 1
        elif r['match']:
            status = "ESLIYOR"
            match_count += 1
        else:
            diff = abs(r['api_price'] - r['db_price'])
            status = f"FARKLI (Fark: {diff:.2f})"
            mismatch_count += 1

        print(f"{date_str:27s} {db_price_str:12s} {api_price_str:12s} {status:20s}")

    print("-"*80)

    total = len(results)
    print(f"\nOzet:")
    print(f"  Esleen       : {match_count} / {total} ({match_count/total*100:.1f}%)")
    print(f"  Farkli        : {mismatch_count} / {total} ({mismatch_count/total*100:.1f}%)")
    print(f"  Hata          : {error_count} / {total} ({error_count/total*100:.1f}%)")

    print("\n" + "="*80)
    print("DEGERLENDIRME")
    print("="*80)

    if match_count / total >= 0.9:
        print("\n VERILER DOGRU!")
        print("    %90+ eslesme var, veritabanindaki degerler guvenilir.")
        print("    0 TRY fiyatlar GERCEK piyasa durumudur.")
        print("\n SONUC:")
        print("    - Verileri oldugu gibi kullanin")
        print("    - Model iyilestirmesi yapilsin (extreme price handling)")
        print("    - Frontend'de aciklama eklensin")
    elif match_count / total >= 0.5:
        print("\n KISMI SORUN!")
        print("    %50-90 arasi eslesme, bazi kayitlar supheli.")
        print("\n SONUC:")
        print("    - Manuel kontrol gerekli")
        print("    - Farkli kayitlari inceleyin")
    else:
        print("\n CIDDI SORUN!")
        print("    %50'den az eslesme, veri kaynagi hatali olabilir.")
        print("\n SONUC:")
        print("    - API endpoint degisikligi gerekli")
        print("    - Veya veri temizleme yapilmali")

    print("="*80)

if __name__ == "__main__":
    verify_suspicious_prices()
