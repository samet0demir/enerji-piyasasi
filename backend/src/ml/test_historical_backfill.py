import contextlib
import io
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from backfill_missing_weeks import find_missing_weeks
from train_prophet_improved import load_data, train_improved_model


class HistoricalTests(unittest.TestCase):
    def test_planner_finds_absent_and_misaligned_weeks(self):
        with contextlib.closing(sqlite3.connect(':memory:')) as conn:
            conn.execute('CREATE TABLE forecast_history (week_start TEXT, forecast_datetime TEXT, predicted_price REAL)')
            for week, offset in [('2026-03-02', 0), ('2026-03-09', 24), ('2026-03-23', 0)]:
                start = datetime.fromisoformat(week) + timedelta(hours=offset)
                conn.executemany('INSERT INTO forecast_history VALUES (?, ?, ?)',
                    [(week, (start + timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S'), 2000)
                     for i in range(168)])
            self.assertEqual(find_missing_weeks(conn, '2026-03-23'), ['2026-03-09', '2026-03-16'])

    def test_future_actual_prices_do_not_change_training_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / 'test.db')
            with contextlib.closing(sqlite3.connect(database)) as conn, conn:
                conn.execute('CREATE TABLE mcp_data (date TEXT, price REAL)')
                conn.executemany('INSERT INTO mcp_data VALUES (?, ?)',
                    [('2026-03-08T23:00:00+03:00', 2000), ('2026-03-09T00:00:00+03:00', 3000),
                     ('2026-03-15T23:00:00+03:00', 4000)])
            with patch('train_prophet_improved.DB_PATH', database):
                before = load_data(end_date='2026-03-09')
                with contextlib.closing(sqlite3.connect(database)) as conn, conn:
                    conn.execute("UPDATE mcp_data SET price=999999 WHERE date >= '2026-03-09'")
                after = load_data(end_date='2026-03-09')
            pd.testing.assert_frame_equal(before, after)
            self.assertEqual(len(after), 1)

    def test_holdout_is_excluded_from_evaluation_model(self):
        frame = pd.DataFrame({'ds': pd.date_range('2026-01-01', periods=500, freq='h'), 'y': 2000.0})
        models = []
        class Model:
            def fit(self, data):
                self.history = data.copy()
            def predict(self, data):
                self.test_dates = data['ds'].copy()
                return data.assign(yhat=2000.0)
        def new_model(holidays):
            model = Model()
            models.append(model)
            return model
        with patch('train_prophet_improved.load_data', return_value=frame), \
             patch('train_prophet_improved.create_model', side_effect=new_model), \
             contextlib.redirect_stdout(io.StringIO()):
            trained, _, _, _ = train_improved_model(end_date='2026-02-01', save_model=False)
        self.assertLess(models[0].history['ds'].max(), models[0].test_dates.min())
        self.assertEqual(len(trained.history), 500)
        self.assertIs(trained, models[1])


if __name__ == '__main__':
    unittest.main()
