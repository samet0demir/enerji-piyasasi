#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basit Forecast JSON - Ham verilerden tahmin oluştur
"""

import pandas as pd
import sqlite3
import json
import os
import sys
from datetime import datetime, timedelta

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '../../public/forecasts.json')

def main():
    print("="*60)
    print("Basit Forecast JSON Oluştur")
    print("="*60)

    # Tahminleri al
    sys.path.insert(0, os.path.dirname(__file__))
    from predict import load_model, make_forecast

    model = load_model()
    forecast_df = make_forecast(model, days=7)

    # Bu hafta tarihleri
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    week_end = (today + timedelta(days=(6-today.weekday()))).strftime('%Y-%m-%d')

    print(f"\n[*] Bu hafta: {week_start} - {week_end}")

    # Tahminleri listeye çevir
    forecasts = []
    for _, row in forecast_df.iterrows():
        forecasts.append({
            'datetime': row['ds'].strftime('%Y-%m-%d %H:%M:%S'),
            'predicted': round(row['yhat'], 2),
            'lower_bound': round(row['yhat_lower'], 2),
            'upper_bound': round(row['yhat_upper'], 2),
            'actual': None
        })

    # Gerçek verileri ekle (varsa)
    conn = sqlite3.connect(DB_PATH)
    actual_query = """
        SELECT date, price
        FROM mcp_data
        ORDER BY date DESC
    """
    actual_df = pd.read_sql_query(actual_query, conn)
    conn.close()

    if len(actual_df) > 0:
        print(f"[+] {len(actual_df)} gerçek veri bulundu")

        # Son 7 günlük gerçek veriyi ekle
        recent_actuals = []
        for _, row in actual_df.head(168).iterrows():  # 7 gün * 24 saat
            recent_actuals.append({
                'datetime': row['date'],
                'predicted': None,
                'actual': round(row['price'], 2)
            })

        # Gerçek verileri forecasts'ın başına ekle
        forecasts = recent_actuals + forecasts

    # JSON oluştur
    output = {
        'generated_at': datetime.now().isoformat(),
        'current_week': {
            'start': week_start,
            'end': week_end,
            'forecasts': forecasts
        },
        'last_week_performance': None,
        'last_week_comparison': [],
        'historical_trend': []
    }

    # Kaydet
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[+] JSON kaydedildi: {OUTPUT_PATH}")
    print(f"[+] Toplam {len(forecasts)} veri noktası")

    # Frontend'e kopyala
    frontend_path = os.path.join(os.path.dirname(__file__), '../../../frontend/public/forecasts.json')
    os.makedirs(os.path.dirname(frontend_path), exist_ok=True)
    with open(frontend_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[+] Frontend'e kopyalandı: {frontend_path}")
    print("="*60)

if __name__ == "__main__":
    main()
