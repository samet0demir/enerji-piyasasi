import { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { ConsumptionData } from '../services/api';
import WeekSelector from '../components/WeekSelector';
import { LineChart, Line, BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import '../App.css';

export function Consumption() {
  const [consumption, setConsumption] = useState<ConsumptionData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWeek, setSelectedWeek] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        let consData;

        if (selectedWeek) {
          // Seçili hafta varsa backend API'den çek
          consData = await api.getConsumptionByWeek(selectedWeek);
        } else {
          // Seçili hafta yoksa default API'den çek
          consData = await api.getConsumption();
        }

        setConsumption(consData);
        setError(null);
      } catch (err: any) {
        console.error('Veri çekme hatası:', err);
        setError(err.message || 'Veriler yüklenirken bir hata oluştu');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [selectedWeek]);

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Veriler yükleniyor...</p>
      </div>
    );
  }

  if (error || consumption.length === 0) {
    return (
      <div className="error-container">
        <h2>⚠️ Hata!</h2>
        <p>{error || 'Tüketim verileri yüklenemedi'}</p>
      </div>
    );
  }

  // Consumption trend (günlük ortalama)
  const consumptionTrend = consumption.reduce((acc: any, item) => {
    const date = item.date.split('T')[0];
    if (!acc[date]) {
      acc[date] = { date, total: 0, count: 0, min: Infinity, max: -Infinity };
    }
    acc[date].total += item.consumption;
    acc[date].count += 1;
    acc[date].min = Math.min(acc[date].min, item.consumption);
    acc[date].max = Math.max(acc[date].max, item.consumption);
    return acc;
  }, {});

  const consumptionChartData = Object.values(consumptionTrend).map((d: any) => ({
    tarih: new Date(d.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' }),
    Ortalama: Math.round(d.total / d.count),
    Min: Math.round(d.min),
    Max: Math.round(d.max)
  }));

  // Saatlik profil (tüm günlerin saatlik ortalaması)
  const hourlyProfile = consumption.reduce((acc: any, item) => {
    const hour = item.hour.substring(0, 2); // "00:00" -> "00"
    if (!acc[hour]) {
      acc[hour] = { hour, total: 0, count: 0 };
    }
    acc[hour].total += item.consumption;
    acc[hour].count += 1;
    return acc;
  }, {});

  const hourlyData = Object.values(hourlyProfile)
    .map((d: any) => ({
      saat: d.hour + ':00',
      tüketim: Math.round(d.total / d.count)
    }))
    .sort((a, b) => a.saat.localeCompare(b.saat));

  // Hafta içi vs hafta sonu (eğer 7 gün varsa)
  const weekdayConsumption: number[] = [];
  const weekendConsumption: number[] = [];

  Object.entries(consumptionTrend).forEach(([dateStr, data]: [string, any]) => {
    const date = new Date(dateStr);
    const dayOfWeek = date.getDay();
    const avg = data.total / data.count;

    if (dayOfWeek === 0 || dayOfWeek === 6) {
      weekendConsumption.push(avg);
    } else {
      weekdayConsumption.push(avg);
    }
  });

  const weekdayAvg = weekdayConsumption.length > 0
    ? Math.round(weekdayConsumption.reduce((a, b) => a + b, 0) / weekdayConsumption.length)
    : 0;
  const weekendAvg = weekendConsumption.length > 0
    ? Math.round(weekendConsumption.reduce((a, b) => a + b, 0) / weekendConsumption.length)
    : 0;

  const weekdayWeekendData = [
    { tip: 'Hafta İçi', ortalama: weekdayAvg },
    { tip: 'Hafta Sonu', ortalama: weekendAvg }
  ].filter(d => d.ortalama > 0);

  // Peak ve Off-Peak saatler
  const peakHours = hourlyData
    .sort((a, b) => b.tüketim - a.tüketim)
    .slice(0, 6);

  const offPeakHours = hourlyData
    .sort((a, b) => a.tüketim - b.tüketim)
    .slice(0, 6);

  // İstatistikler
  const latestData = consumptionChartData[consumptionChartData.length - 1];
  const avgConsumption = latestData ? latestData.Ortalama : 0;
  const totalDailyConsumption = avgConsumption * 24; // Yaklaşık günlük toplam

  const maxConsumption = Math.max(...consumptionChartData.map(d => d.Max));
  const minConsumption = Math.min(...consumptionChartData.map(d => d.Min));

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <h2 className="page-title">📈 Tüketim Analizi</h2>
          <p className="page-subtitle">Elektrik Tüketim Verileri & Trend Analizi (Son 7 Gün)</p>
        </div>
        <div className="update-time">
          Günlük Toplam: ~{totalDailyConsumption.toLocaleString()} MWh
        </div>
      </div>

      {/* Week Selector */}
      <div style={{ padding: '20px 12px 0 12px' }}>
        <WeekSelector
          selectedWeek={selectedWeek}
          onWeekChange={setSelectedWeek}
        />
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card highlight">
          <div className="stat-label">Ortalama Tüketim</div>
          <div className="stat-value">{avgConsumption.toLocaleString()} MWh</div>
          <div className="stat-unit">Saatlik</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Peak Tüketim</div>
          <div className="stat-value">{maxConsumption.toLocaleString()} MWh</div>
          <div className="stat-unit">En yüksek</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Off-Peak Tüketim</div>
          <div className="stat-value">{minConsumption.toLocaleString()} MWh</div>
          <div className="stat-unit">En düşük</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Peak / Off-Peak Oranı</div>
          <div className="stat-value">{(maxConsumption / minConsumption).toFixed(2)}x</div>
          <div className="stat-unit">Varyasyon</div>
        </div>
      </div>

      {/* MAIN: Günlük Tüketim Trendi */}
      <div className="main-chart">
        <div className="chart-header">
          <div>
            <h2>📊 Günlük Tüketim Trendi (Min - Ortalama - Max)</h2>
            <p className="chart-subtitle">
              Her günün minimum, ortalama ve maksimum tüketim değerleri
            </p>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={consumptionChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="tarih" stroke="#94a3b8" style={{ fontSize: '12px' }} />
            <YAxis stroke="#94a3b8" style={{ fontSize: '12px' }} label={{ value: 'Tüketim (MWh)', angle: -90, position: 'insideLeft', fill: '#64748b' }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
              formatter={(value: any) => `${value.toLocaleString()} MWh`}
            />
            <Legend wrapperStyle={{ fontSize: '13px' }} />
            <Area type="monotone" dataKey="Max" stroke="#ef4444" fill="#ef444420" strokeWidth={2} />
            <Area type="monotone" dataKey="Ortalama" stroke="#10b981" fill="#10b98140" strokeWidth={3} />
            <Area type="monotone" dataKey="Min" stroke="#3b82f6" fill="#3b82f620" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Secondary Charts */}
      <div className="charts-grid-secondary">
        {/* Saatlik Profil - Tam Genişlik */}
        <div className="chart-card" style={{ gridColumn: 'span 3' }}>
          <h3>🕐 Saatlik Tüketim Profili</h3>
          <p className="chart-subtitle">24 saatlik ortalama tüketim dağılımı</p>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="saat" stroke="#94a3b8" style={{ fontSize: '11px' }} />
              <YAxis stroke="#94a3b8" style={{ fontSize: '12px' }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                formatter={(value: any) => [`${value.toLocaleString()} MWh`, 'Tüketim']}
              />
              <Bar dataKey="tüketim" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Peak Saatler */}
        <div className="chart-card" style={{ gridColumn: 'span 3' }}>
          <h3>⬆️ Peak Saatler (En Yüksek Tüketim)</h3>
          <p className="chart-subtitle">En yüksek 6 saat</p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={peakHours} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" stroke="#94a3b8" style={{ fontSize: '11px' }} />
              <YAxis type="category" dataKey="saat" stroke="#94a3b8" style={{ fontSize: '11px' }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                formatter={(value: any) => [`${value.toLocaleString()} MWh`, 'Tüketim']}
              />
              <Bar dataKey="tüketim" fill="#ef4444" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Off-Peak Saatler */}
        <div className="chart-card" style={{ gridColumn: 'span 3' }}>
          <h3>⬇️ Off-Peak Saatler (En Düşük Tüketim)</h3>
          <p className="chart-subtitle">En düşük 6 saat</p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={offPeakHours} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" stroke="#94a3b8" style={{ fontSize: '11px' }} />
              <YAxis type="category" dataKey="saat" stroke="#94a3b8" style={{ fontSize: '11px' }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                formatter={(value: any) => [`${value.toLocaleString()} MWh`, 'Tüketim']}
              />
              <Bar dataKey="tüketim" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Günlük Basit Trend */}
        <div className="chart-card" style={{ gridColumn: 'span 2' }}>
          <h3>📈 Günlük Ortalama Trend</h3>
          <p className="chart-subtitle">Son 7 günün ortalama tüketimi</p>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={consumptionChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="tarih" stroke="#94a3b8" style={{ fontSize: '11px' }} />
              <YAxis stroke="#94a3b8" style={{ fontSize: '11px' }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                formatter={(value: any) => [`${value.toLocaleString()} MWh`, 'Ortalama']}
              />
              <Line type="monotone" dataKey="Ortalama" stroke="#10b981" strokeWidth={3} dot={{ fill: '#10b981', r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Hafta İçi vs Hafta Sonu */}
        {weekdayWeekendData.length > 0 && (
          <div className="chart-card">
            <h3>📅 Hafta İçi vs Hafta Sonu</h3>
            <p className="chart-subtitle">Ortalama tüketim karşılaştırması</p>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={weekdayWeekendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="tip" stroke="#94a3b8" style={{ fontSize: '11px' }} />
                <YAxis stroke="#94a3b8" style={{ fontSize: '11px' }} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                  formatter={(value: any) => [`${value.toLocaleString()} MWh`, 'Ortalama']}
                />
                <Bar dataKey="ortalama" fill="#06b6d4" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
