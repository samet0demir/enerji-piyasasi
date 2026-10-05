import contextlib
import importlib
import io
import json
import sqlite3
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from forecast_validation import validate_forecasts


def complete_week():
    start = datetime(2026, 10, 5)
    return {'current_week': {
        'start': '2026-10-05', 'end': '2026-10-11',
        'forecasts': [{'datetime': (start + timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S'),
                       'predicted': 2500.0} for i in range(168)]}}


class PublicationTests(unittest.TestCase):
    def test_complete_week_and_invalid_forecasts(self):
        validate_forecasts(complete_week())
        for case in ('missing', 'duplicate', 'nonfinite', 'wrong_week'):
            data = complete_week()
            rows = data['current_week']['forecasts']
            if case == 'missing':
                rows.pop()
            elif case == 'duplicate':
                rows[-1] = rows[0]
            elif case == 'nonfinite':
                rows[0]['predicted'] = float('nan')
            else:
                data['current_week']['start'] = '2026-10-12'
            with self.subTest(case=case), self.assertRaises(ValueError):
                validate_forecasts(data)

    def test_export_is_strict_and_preserves_files_on_incomplete_week(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / 'test.db'
            with contextlib.closing(sqlite3.connect(database)) as conn, conn:
                conn.executescript('''
                    CREATE TABLE forecast_history (week_start TEXT, forecast_datetime TEXT,
                        predicted_price REAL, actual_price REAL, absolute_error REAL, percentage_error REAL);
                    CREATE TABLE weekly_performance (week_start TEXT, week_end TEXT, mape REAL,
                        mae REAL, rmse REAL, total_predictions INTEGER);
                ''')
                conn.executemany('INSERT INTO forecast_history VALUES (?, ?, ?, NULL, NULL, NULL)',
                    [('2026-10-05', row['datetime'], row['predicted'])
                     for row in complete_week()['current_week']['forecasts']])
                conn.execute('INSERT INTO weekly_performance VALUES (?, ?, ?, ?, ?, ?)',
                    ('2026-09-28', '2026-10-04', float('inf'), 10, 20, 168))
            config = types.ModuleType('db_config')
            config.DB_PATH = str(database)
            sys.modules['db_config'] = config
            try:
                export = importlib.import_module('export_json')
            finally:
                sys.modules.pop('db_config', None)
            backend = root / 'backend.json'
            frontend = root / 'frontend.json'
            with patch.object(export, 'DB_PATH', str(database)), \
                 patch.object(export, 'OUTPUT_PATH', str(backend)), \
                 patch.object(export, 'FRONTEND_PATH', str(frontend)), \
                 patch.object(export, 'get_current_week_monday', return_value='2026-10-05'), \
                 contextlib.redirect_stdout(io.StringIO()):
                export.main()
                previous = backend.read_bytes()
                self.assertEqual(previous, frontend.read_bytes())
                parsed = json.loads(previous, parse_constant=lambda value: self.fail(value))
                self.assertIsNone(parsed['last_week_performance']['mape'])
                with contextlib.closing(sqlite3.connect(database)) as conn, conn:
                    conn.execute('DELETE FROM forecast_history WHERE forecast_datetime = ?',
                                 ('2026-10-11 23:00:00',))
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(ValueError):
                    export.main()
                self.assertEqual(previous, backend.read_bytes())
                self.assertEqual(previous, frontend.read_bytes())

    def test_weekly_export_failure_propagates(self):
        import pandas as pd
        import weekly_workflow_v2 as workflow
        train = types.ModuleType('train_prophet_improved')
        train.main = lambda **kwargs: (object(), 1, 2, 3)
        compare = types.ModuleType('compare_forecasts')
        compare.compare_week = lambda *args: None
        predict = types.ModuleType('predict')
        predict.load_model = lambda: object()
        predict.make_forecast = lambda *args, **kwargs: pd.DataFrame({'yhat': [2500.0]})
        predict.save_forecast_to_db = lambda *args: None
        export = types.ModuleType('export_json')
        def fail_export():
            raise RuntimeError('export failed')
        export.main = fail_export
        backfill = types.ModuleType('backfill_missing_weeks')
        backfill.run_backfill = lambda *args: []
        config = types.ModuleType('db_config')
        config.DB_PATH = ':memory:'
        with patch.dict(sys.modules, {'train_prophet_improved': train, 'predict': predict,
                                     'compare_forecasts': compare, 'export_json': export,
                                     'backfill_missing_weeks': backfill, 'db_config': config}), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
             self.assertRaisesRegex(RuntimeError, 'export failed'):
            workflow.run_weekly_cycle()

    def test_prediction_targets_requested_week_despite_stale_training_data(self):
        import pandas as pd
        serialize = types.ModuleType('prophet.serialize')
        serialize.model_from_json = lambda text: None
        config = types.ModuleType('db_config')
        config.DB_PATH = ':memory:'
        pyplot = types.ModuleType('matplotlib.pyplot')
        matplotlib = types.ModuleType('matplotlib')
        matplotlib.pyplot = pyplot
        with patch.dict(sys.modules, {'prophet': types.ModuleType('prophet'),
                                     'prophet.serialize': serialize, 'db_config': config,
                                     'matplotlib': matplotlib, 'matplotlib.pyplot': pyplot}):
            predict = importlib.import_module('predict')
            class Model:
                history = pd.DataFrame({'ds': pd.to_datetime(['2026-10-02 23:00:00'])})
                def predict(self, future):
                    self.future = future
                    return future.assign(yhat=2500.0)
            model = Model()
            with contextlib.redirect_stdout(io.StringIO()):
                result = predict.make_forecast(model, start_date='2026-10-05')
            self.assertEqual(len(result), 168)
            self.assertEqual(str(result['ds'].min()), '2026-10-05 00:00:00')
            self.assertEqual(str(result['ds'].max()), '2026-10-11 23:00:00')
            self.assertIn('extreme_low_risk', model.future.columns)


if __name__ == '__main__':
    unittest.main()
