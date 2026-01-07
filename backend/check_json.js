import { readFileSync } from 'fs';
const data = JSON.parse(readFileSync('public/forecasts.json'));
const samples = data.current_week.forecasts.slice(24, 30);
console.log('Samples (hours 25-30):');
samples.forEach((s, i) => {
    console.log(`Hour ${i + 25}:`, {
        predicted: Math.round(s.predicted),
        prophet: Math.round(s.prophet),
        lstm: Math.round(s.lstm || 0)
    });
});
