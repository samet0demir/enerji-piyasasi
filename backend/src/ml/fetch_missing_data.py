#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Eksik Veri Toplama - 17-22 Ekim 2025 arası
"""

import sqlite3
import os
import sys
import requests
from datetime import datetime, timedelta

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH
API_BASE = "https://seffaflik.epias.com.tr/electricity-service/v1"

def get_tgt():
    """TGT token al"""
    print("[*] TGT token aliniyor...")

    # TGT credentials (from previous session)
    username = "your_username"  # User should replace this
    password = "your_password"  # User should replace this

    url = "https://giris.epias.com.tr/cas/v1/tickets"
    data = {
        "username": username,
        "password": password
    }

    try:
        response = requests.post(url, data=data)
        if response.status_code == 201:
            tgt = response.headers.get('Location').split('/')[-1]
            print(f"[+] TGT alindi: {tgt[:20]}...")
            return tgt
        else:
            print(f"[!] TGT alinamadi: {response.status_code}")
            print(f"[!] Response: {response.text}")
            return None
    except Exception as e:
        print(f"[!] Hata: {e}")
        return None

def fetch_mcp_data(start_date, end_date, tgt):
    """MCP verilerini cek"""
    print(f"[*] MCP verileri cekiliyor: {start_date} - {end_date}")

    url = f"{API_BASE}/market/day-ahead-mcp"
    headers = {
        "TGT": tgt,
        "Content-Type": "application/json"
    }
    params = {
        "startDate": start_date,
        "endDate": end_date
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            records = data.get('items', [])
            print(f"[+] {len(records)} kayit alindi")
            return records
        else:
            print(f"[!] Veri cekilemedi: {response.status_code}")
            return []
    except Exception as e:
        print(f"[!] Hata: {e}")
        return []

def insert_mcp_data(records):
    """Verileri veritabanina ekle"""
    if not records:
        print("[!] Eklenecek veri yok")
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inserted = 0
    skipped = 0

    for record in records:
        date = record.get('date')
        price = record.get('price')

        if not date or price is None:
            continue

        # Tarih formatini duzenle (ISO 8601 -> SQLite format)
        try:
            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            print(f"[!] Gecersiz tarih: {date}")
            continue

        # Kontrol et: Bu kayit zaten var mi?
        cursor.execute("SELECT COUNT(*) FROM mcp_data WHERE date = ?", (date_str,))
        exists = cursor.fetchone()[0]

        if exists > 0:
            skipped += 1
            continue

        # Ekle
        cursor.execute("""
            INSERT INTO mcp_data (date, price)
            VALUES (?, ?)
        """, (date_str, price))
        inserted += 1

    conn.commit()
    conn.close()

    print(f"[+] {inserted} yeni kayit eklendi")
    print(f"[*] {skipped} kayit zaten mevcut")

    return inserted

def main():
    """Ana fonksiyon"""
    print("="*60)
    print("EKSIK VERI TOPLAMA - 17-22 Ekim 2025")
    print("="*60)

    # Tarih araligini hesapla
    # 17 Ekim 00:00 - 22 Ekim 23:00
    start_date = "2025-10-17T00:00:00Z"
    end_date = "2025-10-22T23:59:59Z"

    print(f"\n[*] Tarih Araligi: {start_date} - {end_date}")
    print(f"[*] Toplam: 6 gun x 24 saat = 144 saat")

    # TGT al
    tgt = get_tgt()
    if not tgt:
        print("\n[!] TGT alinamadi. Lutfen credentials kontrol edin.")
        sys.exit(1)

    # MCP verilerini cek
    records = fetch_mcp_data(start_date, end_date, tgt)

    # Veritabanina ekle
    inserted = insert_mcp_data(records)

    # Ozet
    print("\n" + "="*60)
    print("TOPLAMA TAMAMLANDI")
    print("="*60)
    print(f"Toplam kayit: {len(records)}")
    print(f"Eklenen    : {inserted}")
    print(f"Mevcut     : {len(records) - inserted}")

    # Veritabani durumu
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM mcp_data")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(date), MAX(date) FROM mcp_data")
    min_date, max_date = cursor.fetchone()

    conn.close()

    print(f"\nVeritabani Durumu:")
    print(f"  Toplam kayit: {total}")
    print(f"  Tarih araligi: {min_date} - {max_date}")
    print("="*60)

    if inserted > 0:
        print("\n[*] Sira geldi: Modeli yeniden egitmek!")
        print("    Calistir: python src/ml/train_prophet.py")

if __name__ == "__main__":
    main()
