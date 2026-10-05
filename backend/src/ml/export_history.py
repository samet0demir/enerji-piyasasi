"""Publish all weekly predictions and their retrospective provenance."""

import json
import math
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from db_config import DB_PATH
from forecast_validation import validate_forecasts


def finite(value):
    return round(value, 2) if value is not None and math.isfinite(value) else None


def export_history():
    weeks = []
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        has_provenance = conn.execute("SELECT 1 FROM sqlite_master WHERE name='forecast_provenance'").fetchone()
        for week in conn.execute('SELECT DISTINCT week_start, week_end FROM forecast_history ORDER BY week_start DESC'):
            rows = conn.execute('SELECT * FROM forecast_history WHERE week_start=? ORDER BY forecast_datetime',
                                (week['week_start'],)).fetchall()
            forecasts = [{'datetime': row['forecast_datetime'], 'predicted': finite(row['predicted_price']),
                          'actual': finite(row['actual_price']), 'error': finite(row['absolute_error']),
                          'error_percent': finite(row['percentage_error'])} for row in rows]
            validate_forecasts({'current_week': {'start': week['week_start'], 'end': week['week_end'],
                                                'forecasts': forecasts}})
            performance = conn.execute('SELECT * FROM weekly_performance WHERE week_start=?',
                                       (week['week_start'],)).fetchone()
            if performance:
                performance = {'week_start': week['week_start'], 'week_end': week['week_end'],
                    'mape': finite(performance['mape']), 'mae': finite(performance['mae']),
                    'rmse': finite(performance['rmse']), 'total_predictions': performance['total_predictions']}
            metadata = conn.execute('SELECT metadata FROM forecast_provenance WHERE week_start=?',
                                    (week['week_start'],)).fetchone() if has_provenance else None
            weeks.append({'week_start': week['week_start'], 'week_end': week['week_end'],
                          'forecasts': forecasts, 'performance': performance,
                          'provenance': json.loads(metadata[0]) if metadata else None})
    payload = {'generated_at': datetime.now(timezone.utc).isoformat(), 'weeks': weeks}
    content = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
    for relative in ('../../public/forecast-history.json', '../../../frontend/public/forecast-history.json'):
        target = os.path.join(os.path.dirname(__file__), relative)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'w', encoding='utf-8', newline='\n') as output:
            output.write(content)
    print(f'Published {len(weeks)} complete forecast weeks')
    return payload


if __name__ == '__main__':
    export_history()
