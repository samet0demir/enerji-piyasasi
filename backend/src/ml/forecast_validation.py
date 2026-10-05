"""Validate a complete hourly forecast before publishing it."""

import math
from datetime import datetime, timedelta


def validate_forecasts(data):
    week = data['current_week']
    start = datetime.strptime(week['start'], '%Y-%m-%d')
    expected = [(start + timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S')
                for i in range(7 * 24)]
    forecasts = week['forecasts']
    if week['end'] != (start + timedelta(days=6)).strftime('%Y-%m-%d'):
        raise ValueError('Forecast week end does not match the start date')
    if [row['datetime'] for row in forecasts] != expected:
        raise ValueError('Forecast must contain all 168 hours of the requested week')
    if any(not isinstance(row['predicted'], (int, float))
           or not math.isfinite(row['predicted']) for row in forecasts):
        raise ValueError('Forecast contains invalid predicted prices')
