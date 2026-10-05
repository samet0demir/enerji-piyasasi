#!/usr/bin/env python
"""Discover and repair historical forecast gaps without using future prices."""
import argparse
from datetime import datetime, timedelta
from backfill_missing_weeks import run_backfill
from db_config import DB_PATH


def main():
    today = datetime.now()
    monday = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--through', default=monday)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run_backfill(DB_PATH, args.through, args.dry_run)
    if not args.dry_run:
        from export_json import main as export_current
        from export_history import export_history
        export_current()
        export_history()


if __name__ == '__main__':
    main()
