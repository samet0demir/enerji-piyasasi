import Database from 'better-sqlite3';

const db = new Database('./data/energy.db');

console.log('=== FINAL VERIFICATION ===\n');

// Check all weeks status
const weeks = db.prepare(`
  SELECT 
    week_start, 
    week_end, 
    COUNT(*) as total, 
    COUNT(actual_price) as with_actual 
  FROM forecast_history 
  GROUP BY week_start 
  ORDER BY week_start DESC
  LIMIT 4
`).all();

console.log('FORECAST HISTORY STATUS:');
weeks.forEach(w => {
  const status = w.total === w.with_actual ? '✅ COMPLETE' : '⏳ ONGOING';
  console.log(`  ${w.week_start} → ${w.week_end}: ${w.with_actual}/${w.total} ${status}`);
});

console.log('\nWEEKLY PERFORMANCE:');
const perf = db.prepare(`
  SELECT week_start, mape, mae, rmse
  FROM weekly_performance
  ORDER BY week_start DESC
  LIMIT 4
`).all();

perf.forEach(p => {
  console.log(`  ${p.week_start}: MAPE=${p.mape.toFixed(2)}%, MAE=${p.mae.toFixed(2)} TRY`);
});

db.close();
