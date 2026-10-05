"""Repair absent/incomplete weeks using only observations before each Monday."""

from contextlib import closing
import argparse
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from forecast_validation import validate_forecasts


def find_missing_weeks(conn, through):
    first = conn.execute('SELECT MIN(week_start) FROM forecast_history').fetchone()[0]
    if not first:
        raise ValueError('No forecast start date found; choose the historical scope explicitly')
    monday = datetime.strptime(first, '%Y-%m-%d')
    end = datetime.strptime(through, '%Y-%m-%d')
    missing = []
    while monday <= end:
        start = monday.strftime('%Y-%m-%d')
        sunday = (monday + timedelta(days=6)).strftime('%Y-%m-%d')
        rows = conn.execute('SELECT forecast_datetime, predicted_price FROM forecast_history '
                            'WHERE week_start=? ORDER BY forecast_datetime', (start,)).fetchall()
        try:
            validate_forecasts({'current_week': {'start': start, 'end': sunday,
                'forecasts': [{'datetime': row[0], 'predicted': row[1]} for row in rows]}})
        except ValueError:
            missing.append(start)
        monday += timedelta(weeks=1)
    return missing


def run_backfill(db_path, through, dry_run=False):
    os.environ['DB_PATH'] = os.path.abspath(db_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        weeks = find_missing_weeks(conn, through)
    print('Weeks to repair:', ', '.join(weeks) or 'none', flush=True)
    if dry_run:
        return weeks

    import train_prophet_improved as training
    import predict as prediction
    import compare_forecasts as comparison
    for module in (training, prediction, comparison):
        module.DB_PATH = os.path.abspath(db_path)
    audit = []
    for start in weeks:
        end = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')
        with closing(sqlite3.connect(db_path)) as conn, conn:
            observations = conn.execute('SELECT date, price FROM mcp_data WHERE date < ? '
                                        'ORDER BY date', (start,)).fetchall()
        if len(observations) < 168:
            raise ValueError(f'Insufficient training history for {start}')
        latest = datetime.fromisoformat(observations[-1][0]).replace(tzinfo=None)
        if latest >= datetime.strptime(start, '%Y-%m-%d'):
            raise ValueError('Training cutoff violated')
        digest = hashlib.sha256(json.dumps(observations, separators=(',', ':')).encode()).hexdigest()
        model, _, _, _ = training.train_improved_model(end_date=start, save_model=False, evaluate=False)
        if model.history['ds'].max().to_pydatetime() >= datetime.strptime(start, '%Y-%m-%d'):
            raise ValueError('Fitted model contains future observations')
        forecasts = prediction.make_forecast(model, days=7, start_date=start)
        validate_forecasts({'current_week': {'start': start, 'end': end, 'forecasts': [
            {'datetime': row.ds.strftime('%Y-%m-%d %H:%M:%S'), 'predicted': float(row.yhat)}
            for row in forecasts.itertuples()]}})
        forecasts['prophet_component'] = forecasts['yhat']
        prediction.save_forecast_to_db(forecasts, start, end)
        # Actual prices are read only after all forecasts are fixed and saved.
        performance = comparison.compare_week(start, end)
        record = {'week_start': start, 'week_end': end, 'kind': 'retrospective',
                  'training_cutoff_exclusive': start, 'training_latest': observations[-1][0],
                  'training_rows': len(observations), 'training_sha256': digest,
                  'forecast_rows': len(forecasts), 'model': 'prophet-v2',
                  'generated_at': datetime.now(timezone.utc).isoformat()}
        with closing(sqlite3.connect(db_path)) as conn, conn:
            conn.execute('CREATE TABLE IF NOT EXISTS forecast_provenance '
                         '(week_start TEXT PRIMARY KEY, metadata TEXT NOT NULL)')
            conn.execute('INSERT OR REPLACE INTO forecast_provenance VALUES (?, ?)',
                         (start, json.dumps(record)))
        audit.append(record)
        print(f'REPAIRED {start}: 168 hours; training latest={latest}; '
              f'comparison rows={performance["total_predictions"] if performance else 0}', flush=True)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        remaining = find_missing_weeks(conn, through)
    if remaining:
        raise ValueError(f'Incomplete weeks remain: {remaining}')
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--through', required=True, help='Last Monday to check (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run_backfill(args.db, args.through, args.dry_run)
