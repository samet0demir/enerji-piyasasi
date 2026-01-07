import { readFileSync } from 'fs';
import Database from 'better-sqlite3';

const db = new Database('./data/energy.db');

console.log('=== GÜNCEL HAFTA ANALİZİ ===\n');

// 1. forecasts.json'daki güncel hafta
const json = JSON.parse(readFileSync('public/forecasts.json'));
console.log('JSON Güncel Hafta:', json.current_week.start, '-', json.current_week.end);
console.log('Üretim Tarihi:', json.generated_at);
console.log('Tahmin Sayısı:', json.current_week.forecasts.length);

// 2. MCP_DATA - Bu hafta için gerçek veriler
const thisWeekActual = db.prepare(`
  SELECT COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date
  FROM mcp_data 
  WHERE date >= '2026-01-06' AND date < '2026-01-13'
`).get();
console.log('\nMCP_DATA (Bu hafta gerçek):', thisWeekActual);

// 3. Forecast_history - Bu hafta için veritabanındaki tahminler
const forecastHistory = db.prepare(`
  SELECT 
    COUNT(*) as total,
    COUNT(actual_price) as with_actual,
    week_start, week_end
  FROM forecast_history 
  WHERE week_start = '2026-01-06'
`).get();
console.log('Forecast_history (Bu hafta):', forecastHistory);

// 4. Bugünkü gerçek MCP verileri
const todayData = db.prepare(`
  SELECT date, hour, price FROM mcp_data 
  WHERE date LIKE '2026-01-07%'
  ORDER BY date
  LIMIT 5
`).all();
console.log('\nBugünkü gerçek veriler (örnek):');
todayData.forEach(d => console.log(`  ${d.date}: ${d.price} TRY`));

db.close();
