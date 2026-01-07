import { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { ForecastsResponse, WeeklyPerformance } from '../services/api';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import WeekSelector from '../components/WeekSelector';
import '../App.css';

export function Dashboard() {
  const [data, setData] = useState<ForecastsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWeek, setSelectedWeek] = useState<string | null>(null);
  const [weeklyPerformance, setWeeklyPerformance] = useState<WeeklyPerformance[]>([]);

  // Date range filter for table
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [showTable, setShowTable] = useState(false);

  // MAPE değerine göre renk sınıfı döndür
  const getMapeColorClass = (mape: number): string => {
    if (mape < 10) return 'mape-excellent';  // Mükemmel - Koyu yeşil
    if (mape < 20) return 'mape-good';       // İyi - Yeşil
    if (mape < 30) return 'mape-average';    // Orta - Sarı
    if (mape < 40) return 'mape-poor';       // Zayıf - Turuncu
    return 'mape-bad';                       // Kötü - Kırmızı
  };

  // Haftalık performans verisini çek (bir kere)
  useEffect(() => {
    const fetchPerformance = async () => {
      const perf = await api.getWeeklyPerformance();
      setWeeklyPerformance(perf);
    };
    fetchPerformance();
  }, []);

  // Seçili hafta değiştiğinde veri çek
  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        let forecastData;

        if (selectedWeek) {
          // Seçili hafta varsa backend API'den çek
          forecastData = await api.getWeekData(selectedWeek);
        } else {
          // Seçili hafta yoksa default JSON'dan çek
          forecastData = await api.getForecasts();
        }

        setData(forecastData);
        setError(null);
      } catch (err: any) {
        console.error('Veri çekme hatası:', err);
        setError(err.message || 'Veriler yüklenirken bir hata oluştu');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [selectedWeek]); // selectedWeek değiştiğinde yeniden çalışır

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Veriler yükleniyor...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="error-container">
        <h2>⚠️ Hata!</h2>
        <p>{error || 'Veriler yüklenemedi'}</p>
      </div>
    );
  }

  // Günlük ortalama tahminler (7 gün)
  const dailyForecastData = data.current_week.forecasts.reduce((acc: any[], item) => {
    const date = item.datetime.split(' ')[0];
    const existing = acc.find(d => d.date === date);
    if (existing) {
      existing.total += item.predicted;
      existing.count += 1;
    } else {
      acc.push({ date, total: item.predicted, count: 1 });
    }
    return acc;
  }, []).map(d => ({
    gün: new Date(d.date).toLocaleDateString('tr-TR', { weekday: 'short', day: 'numeric' }),
    fiyat: Math.round(d.total / d.count)
  }));

  // Saatlik karşılaştırma (tahmin vs gerçek) - TÜM DETAY
  const hourlyComparisonData = data.last_week_comparison.map((item, idx) => ({
    saat: new Date(item.datetime).toLocaleDateString('tr-TR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit'
    }),
    index: idx + 1,
    Tahmin: Math.round(item.predicted),
    Gerçek: Math.round(item.actual),
    Hata: Math.abs(Math.round(item.error))
  }));

  // Hata dağılımı analizi
  const errorRanges = {
    '0-100': 0,
    '100-300': 0,
    '300-500': 0,
    '500+': 0
  };

  data.last_week_comparison.forEach(item => {
    const absError = Math.abs(item.error);
    if (absError < 100) errorRanges['0-100']++;
    else if (absError < 300) errorRanges['100-300']++;
    else if (absError < 500) errorRanges['300-500']++;
    else errorRanges['500+']++;
  });

  const errorDistribution = Object.entries(errorRanges).map(([range, count]) => ({
    aralık: range + ' ₺',
    adet: count
  }));

  // Performance trend - API'den gelen haftalık performans verisi
  const trendData = [...weeklyPerformance]
    .sort((a, b) => a.week_start.localeCompare(b.week_start)) // En eski haftayı sola al
    .map(w => {
      const startDate = new Date(w.week_start);
      const endDate = new Date(w.week_end);
      const months = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];

      // Aynı ay içindeyse: "20-26 Eki", farklı aylardaysa: "27 Eki-2 Kas"
      if (startDate.getMonth() === endDate.getMonth()) {
        return {
          hafta: `${startDate.getDate()}-${endDate.getDate()} ${months[startDate.getMonth()]}`,
          MAPE: parseFloat(w.mape.toFixed(1))
        };
      } else {
        return {
          hafta: `${startDate.getDate()} ${months[startDate.getMonth()]}-${endDate.getDate()} ${months[endDate.getMonth()]}`,
          MAPE: parseFloat(w.mape.toFixed(1))
        };
      }
    });

  // Filtered table data based on date range
  const filteredTableData = data.last_week_comparison.filter(item => {
    if (!startDate && !endDate) return true;
    const itemDate = item.datetime.split(' ')[0];
    const start = startDate || '2000-01-01';
    const end = endDate || '2099-12-31';
    return itemDate >= start && itemDate <= end;
  });

  // Stats
  const currentStats = {
    avg: Math.round(data.current_week.forecasts.reduce((s, f) => s + f.predicted, 0) / data.current_week.forecasts.length),
    min: Math.round(Math.min(...data.current_week.forecasts.map(f => f.predicted))),
    max: Math.round(Math.max(...data.current_week.forecasts.map(f => f.predicted)))
  };

  const lastWeekPerf = data.last_week_performance;

  return (
    <div className="page-content">
      {/* Header with update time */}
      <div className="page-header">
        <div>
          <h2 className="page-title">📊 Genel Bakış & Tahmin Performansı</h2>
          <p className="page-subtitle">AI Tabanlı Enerji Fiyat Tahmini & Karşılaştırma</p>
        </div>
        <div className="update-time">
          Son Güncelleme: {new Date(data.generated_at).toLocaleString('tr-TR', {
            day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
          })}
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
        <div className="stat-card">
          <div className="stat-label">Ortalama Tahmin</div>
          <div className="stat-value">{currentStats.avg.toLocaleString()} ₺</div>
          <div className="stat-unit">MWh</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Min - Max</div>
          <div className="stat-value">{currentStats.min} - {currentStats.max} ₺</div>
          <div className="stat-unit">MWh</div>
        </div>
        {lastWeekPerf && (
          <>
            <div className={`stat-card ${getMapeColorClass(lastWeekPerf.mape ?? 100)}`}>
              <div className="stat-label">Model MAPE</div>
              <div className="stat-value">{typeof lastWeekPerf.mape === 'number' ? lastWeekPerf.mape.toFixed(1) : '--'}%</div>
              <div className="stat-unit">
                {typeof lastWeekPerf.mape === 'number' ? (
                  lastWeekPerf.mape < 10 ? '✓ Mükemmel' :
                    lastWeekPerf.mape < 20 ? '✓ İyi' :
                      lastWeekPerf.mape < 30 ? '~ Orta' :
                        lastWeekPerf.mape < 40 ? '⚠ Zayıf' : '✗ Kötü'
                ) : 'Veri Yok'}
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">MAE / RMSE</div>
              <div className="stat-value">
                {typeof lastWeekPerf.mae === 'number' ? Math.round(lastWeekPerf.mae) : '--'} / {typeof lastWeekPerf.rmse === 'number' ? Math.round(lastWeekPerf.rmse) : '--'} ₺
              </div>
              <div className="stat-unit">{lastWeekPerf.total_predictions} tahmin</div>
            </div>
          </>
        )}
      </div>

      {/* MAIN: Tahmin vs Gerçek - Tam Genişlik */}
      {
        hourlyComparisonData.length > 0 && (
          <div className="main-chart">
            <div className="chart-header">
              <div>
                <h2>📊 Geçen Hafta: Tahmin vs Gerçek Performansı (Saatlik Detay)</h2>
                <p className="chart-subtitle">
                  {data.last_week_comparison.length} saatlik veri noktası |
                  Ortalama Hata: {Math.round(data.last_week_comparison.reduce((s, i) => s + Math.abs(i.error), 0) / data.last_week_comparison.length)} ₺ |
                  En Büyük Hata: {Math.round(Math.max(...data.last_week_comparison.map(i => Math.abs(i.error))))} ₺
                </p>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={380}>
              <LineChart data={hourlyComparisonData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis
                  dataKey="index"
                  stroke="#94a3b8"
                  style={{ fontSize: '11px' }}
                  label={{ value: 'Saat', position: 'insideBottom', offset: -5, fill: '#64748b' }}
                />
                <YAxis
                  stroke="#94a3b8"
                  style={{ fontSize: '11px' }}
                  label={{ value: 'Fiyat (₺/MWh)', angle: -90, position: 'insideLeft', fill: '#64748b' }}
                />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                  formatter={(value: any) => `${value} ₺`}
                />
                <Legend wrapperStyle={{ color: '#94a3b8', fontSize: '13px' }} />
                <Line type="monotone" dataKey="Tahmin" stroke="#3b82f6" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="Gerçek" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )
      }

      {/* Data Explorer - Date Range Table */}
      <div className="data-explorer">
        <div className="explorer-header">
          <h3>🔍 Veri Gezgini - Detaylı Karşılaştırma</h3>
          <div className="date-controls">
            <label>
              Başlangıç:
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="date-input"
              />
            </label>
            <label>
              Bitiş:
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="date-input"
              />
            </label>
            <button
              onClick={() => setShowTable(!showTable)}
              className="toggle-btn"
            >
              {showTable ? '📊 Grafik Görünümü' : '📋 Tablo Görünümü'}
            </button>
            <button
              onClick={() => { setStartDate(''); setEndDate(''); }}
              className="reset-btn"
            >
              🔄 Sıfırla
            </button>
          </div>
        </div>

        {showTable && (
          <div className="data-table-container">
            <p className="table-info">
              Gösterilen: {filteredTableData.length} / {data.last_week_comparison.length} kayıt
            </p>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Tarih & Saat</th>
                    <th>Tahmin (₺)</th>
                    <th>Gerçek (₺)</th>
                    <th>Fark (₺)</th>
                    <th>Hata %</th>
                    <th>Durum</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTableData.map((item, idx) => {
                    const accuracy = 100 - Math.abs(item.error_percent);
                    const status =
                      accuracy > 90 ? '🟢 Mükemmel' :
                        accuracy > 80 ? '🟡 İyi' :
                          accuracy > 70 ? '🟠 Orta' : '🔴 Zayıf';

                    return (
                      <tr key={idx}>
                        <td>{idx + 1}</td>
                        <td>{new Date(item.datetime).toLocaleString('tr-TR')}</td>
                        <td className="value-cell">{item.predicted.toFixed(2)}</td>
                        <td className="value-cell">{item.actual.toFixed(2)}</td>
                        <td className={`value-cell ${item.error > 0 ? 'negative' : 'positive'}`}>
                          {item.error > 0 ? '+' : ''}{item.error.toFixed(2)}
                        </td>
                        <td className={`value-cell ${Math.abs(item.error_percent) < 10 ? 'good' : Math.abs(item.error_percent) < 20 ? 'medium' : 'bad'}`}>
                          {item.error_percent.toFixed(2)}%
                        </td>
                        <td>{status}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Secondary Charts Grid */}
      <div className="charts-grid-secondary">
        {/* Hata Dağılımı */}
        <div className="chart-card">
          <h3>📉 Hata Dağılımı Analizi</h3>
          <p className="chart-subtitle">Tahmin hatalarının aralıklara göre dağılımı</p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={errorDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="aralık" stroke="#94a3b8" style={{ fontSize: '11px' }} />
              <YAxis stroke="#94a3b8" style={{ fontSize: '11px' }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                formatter={(value: any) => [`${value} saat`, 'Adet']}
              />
              <Bar dataKey="adet" fill="#ef4444" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Model Bileşenleri Karşılaştırması */}
        <div className="chart-card">
          <h3>🤖 Model Bileşenleri (Bu Hafta)</h3>
          <p className="chart-subtitle">
            Prophet + XGBoost + LSTM Ensemble
          </p>
          {/* Model bileşenleri sadece JSON'dan (seçili hafta yokken) gelir */}
          {data.current_week.forecasts[24]?.prophet ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.current_week.forecasts.slice(24, 96).map((f: any, idx: number) => ({
                saat: idx + 25,
                Ensemble: Math.round(f.predicted || 0),
                Prophet: Math.round(f.prophet || 0),
                LSTM: Math.round(f.lstm || 0)
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="saat" stroke="#94a3b8" style={{ fontSize: '10px' }} />
                <YAxis stroke="#94a3b8" style={{ fontSize: '11px' }} domain={[1500, 4000]} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                  formatter={(value: any, name: string) => [`${value.toLocaleString()} ₺`, name]}
                />
                <Legend />
                <Line type="monotone" dataKey="Ensemble" stroke="#10b981" strokeWidth={2.5} dot={false} name="Ensemble (Final)" />
                <Line type="monotone" dataKey="Prophet" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="Prophet" />
                <Line type="monotone" dataKey="LSTM" stroke="#f59e0b" strokeWidth={1.5} dot={false} name="LSTM" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
              <div style={{ textAlign: 'center' }}>
                <p>📊 Model bileşenleri sadece güncel hafta için gösterilir.</p>
                <p style={{ fontSize: '12px', marginTop: '8px' }}>Güncel tahminleri görmek için hafta seçimini kaldırın.</p>
              </div>
            </div>
          )}
        </div>

        {/* Performance Trend */}
        {trendData.length > 0 && (
          <div className="chart-card">
            <h3>📊 Model Performans Trendi</h3>
            <p className="chart-subtitle">Haftalık MAPE değerleri</p>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="hafta" stroke="#94a3b8" style={{ fontSize: '11px' }} />
                <YAxis stroke="#94a3b8" style={{ fontSize: '11px' }} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                  formatter={(value: any) => [`${value}%`, 'MAPE']}
                />
                <Bar dataKey="MAPE" fill="#f59e0b" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div >
  );
}
