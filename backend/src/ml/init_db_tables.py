#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Table Initialization
==============================
Creates forecast_history and weekly_performance tables if they don't exist.
"""

import sqlite3
import os
import sys

# Database path configuration
try:
    from db_config import DB_PATH
except ImportError:
    # If running from ml/ directory directly
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from db_config import DB_PATH

def init_forecast_tables():
    """Create forecast_history and weekly_performance tables"""

    print("="*70)
    print("DATABASE TABLE INITIALIZATION")
    print("="*70)
    print(f"Database: {DB_PATH}")
    print()

    conn = sqlite3.connect(DB_PATH)

    # Create forecast_history table
    print("[1/2] Creating forecast_history table...")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS forecast_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start DATE NOT NULL,
            week_end DATE NOT NULL,
            forecast_datetime TEXT NOT NULL,
            predicted_price REAL NOT NULL,
            actual_price REAL,
            absolute_error REAL,
            percentage_error REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(week_start, forecast_datetime)
        )
    ''')
    print("[OK] forecast_history table created")

    # Create weekly_performance table
    print("[2/2] Creating weekly_performance table...")
    conn.execute('''
        CREATE TABLE IF NOT EXISTS weekly_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start DATE NOT NULL,
            week_end DATE NOT NULL,
            mape REAL NOT NULL,
            mae REAL NOT NULL,
            rmse REAL NOT NULL,
            total_predictions INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(week_start)
        )
    ''')
    print("[OK] weekly_performance table created")

    conn.commit()
    conn.close()

    print()
    print("="*70)
    print("[DONE] Database tables initialized successfully!")
    print("="*70)

if __name__ == "__main__":
    init_forecast_tables()
