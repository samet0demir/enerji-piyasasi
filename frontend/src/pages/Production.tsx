import { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { GenerationData } from '../services/api';
import WeekSelector from '../components/WeekSelector';
import { AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import '../App.css';

const COLORS = {
  'Güneş': '#f59e0b',
  'Rüzgar': '#06b6d4',
  'Hidro': '#3b82f6',
  'Doğalgaz': '#8b5cf6',
  'Linyit': '#6b7280',
  'Jeotermal': '#ef4444'
};

export function Production() {
  const [generation, setGeneration] = useState<GenerationData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWeek, setSelectedWeek] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        let genData;

        if (selectedWeek) {
          // Seçili hafta varsa backend API'den çek
          genData = await api.getGenerationByWeek(selectedWeek);
        } else {
          // Seçili hafta yoksa default API'den çek
          genData = await api.getGeneration();
        }

        setGeneration(genData);
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

  if (error || generation.length === 0) {
    return (
      <div className="error-container">
        <h2>Hata</h2>
        <p>{error || 'Üretim verileri yüklenemedi'}</p>
      </div>
    );
  }

  // Generation mix chart (günlük ortalama)
  const generationMix = generation.reduce((acc: any, item) => {
    const date = item.date.split('T')[0];
    if (!acc[date]) {
      acc[date] = {
        date,
        Güneş: 0, Rüzgar: 0, Hidro: 0, Doğalgaz: 0, Linyit: 0, Jeotermal: 0, count: 0
      };
    }
    acc[date].Güneş += item.solar || 0;
    acc[date].Rüzgar += item.wind || 0;
    acc[date].Hidro += item.hydro || 0;
    acc[date].Doğalgaz += item.natural_gas || 0;
    acc[date].Linyit += item.lignite || 0;
    acc[date].Jeotermal += item.geothermal || 0;
    acc[date].count += 1;
    return acc;
  }, {});

  const generationChartData = Object.values(generationMix).map((d: any) => ({
    tarih: new Date(d.date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' }),
    Güneş: Math.round(d.Güneş / d.count),
    Rüzgar: Math.round(d.Rüzgar / d.count),
    Hidro: Math.round(d.Hidro / d.count),
    Doğalgaz: Math.round(d.Doğalgaz / d.count),
    Linyit: Math.round(d.Linyit / d.count),
    Jeotermal: Math.round(d.Jeotermal / d.count)
  }));

  // Toplam üretim trendi
  const totalGeneration = generationChartData.map(d => ({
    tarih: d.tarih,
    toplam: d.Güneş + d.Rüzgar + d.Hidro + d.Doğalgaz + d.Linyit + d.Jeotermal
  }));

  // Kaynak bazında ortalama paylar (pie chart için)
  const avgSources = {
    Güneş: 0, Rüzgar: 0, Hidro: 0, Doğalgaz: 0, Linyit: 0, Jeotermal: 0
  };

  generationChartData.forEach(d => {
    avgSources.Güneş += d.Güneş;
    avgSources.Rüzgar += d.Rüzgar;
    avgSources.Hidro += d.Hidro;
    avgSources.Doğalgaz += d.Doğalgaz;
    avgSources.Linyit += d.Linyit;
    avgSources.Jeotermal += d.Jeotermal;
  });

  const pieData = Object.entries(avgSources).map(([name, value]) => ({
    name,
    value: Math.round(value / generationChartData.length)
  })).filter(d => d.value > 0);

  // Her kaynak için trend (son 7 gün)
  const sourcesTrend = [
    { name: 'Güneş', data: generationChartData.map(d => ({ tarih: d.tarih, değer: d.Güneş })), color: COLORS['Güneş'] },
    { name: 'Rüzgar', data: generationChartData.map(d => ({ tarih: d.tarih, değer: d.Rüzgar })), color: COLORS['Rüzgar'] },
    { name: 'Hidro', data: generationChartData.map(d => ({ tarih: d.tarih, değer: d.Hidro })), color: COLORS['Hidro'] },
    { name: 'Doğalgaz', data: generationChartData.map(d => ({ tarih: d.tarih, değer: d.Doğalgaz })), color: COLORS['Doğalgaz'] },
    { name: 'Linyit', data: generationChartData.map(d => ({ tarih: d.tarih, değer: d.Linyit })), color: COLORS['Linyit'] },
    { name: 'Jeotermal', data: generationChartData.map(d => ({ tarih: d.tarih, değer: d.Jeotermal })), color: COLORS['Jeotermal'] }
  ];

  // İstatistikler - HAFTALIK ORTALAMA (tüm günlerin ortalaması)
  const weeklyAvg = {
    Güneş: 0, Rüzgar: 0, Hidro: 0, Doğalgaz: 0, Linyit: 0, Jeotermal: 0
  };

  generationChartData.forEach(d => {
    weeklyAvg.Güneş += d.Güneş;
    weeklyAvg.Rüzgar += d.Rüzgar;
    weeklyAvg.Hidro += d.Hidro;
    weeklyAvg.Doğalgaz += d.Doğalgaz;
    weeklyAvg.Linyit += d.Linyit;
    weeklyAvg.Jeotermal += d.Jeotermal;
  });

  const dayCount = generationChartData.length || 1;
  const avgData = {
    Güneş: Math.round(weeklyAvg.Güneş / dayCount),
    Rüzgar: Math.round(weeklyAvg.Rüzgar / dayCount),
    Hidro: Math.round(weeklyAvg.Hidro / dayCount),
    Doğalgaz: Math.round(weeklyAvg.Doğalgaz / dayCount),
    Linyit: Math.round(weeklyAvg.Linyit / dayCount),
    Jeotermal: Math.round(weeklyAvg.Jeotermal / dayCount)
  };

  const totalProduction = Object.values(avgData).reduce((sum, val) => sum + val, 0);

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <h2 className="page-title">Uretim Analizi</h2>
          <p className="page-subtitle">Kaynak Bazında Elektrik Üretim Verileri (Son 7 Gün)</p>
        </div>
        <div className="update-time">
          Toplam Üretim: {totalProduction.toLocaleString()} MWh/gün (haftalık ort.)
        </div>
      </div>

      {/* Week Selector */}
      <div style={{ padding: '20px 12px 0 12px' }}>
        <WeekSelector
          selectedWeek={selectedWeek}
          onWeekChange={setSelectedWeek}
        />
      </div>

      {/* Stats Grid - HAFTALIK ORTALAMA */}
      <div className="stats-grid">
        {Object.entries(avgData)
          .filter(([, value]) => value > 0)
          .map(([source, value]) => {
            const percentage = ((value as number) / totalProduction * 100).toFixed(1);
            return (
              <div key={source} className="stat-card">
                <div className="stat-label" style={{ color: COLORS[source as keyof typeof COLORS] }}>
                  {source}
                </div>
                <div className="stat-value">{(value as number).toLocaleString()} MWh</div>
                <div className="stat-unit">%{percentage} pay (haftalık ort.)</div>
              </div>
            );
          })}
      </div>

      {/* MAIN: Kaynak Dağılımı - Stacked Area Chart */}
      <div className="main-chart">
        <div className="chart-header">
          <div>
            <h2>Uretim Kaynaklari Dagilimi (Gunluk Ortalama)</h2>
            <p className="chart-subtitle">
              Kaynak bazında saatlik ortalama elektrik üretimi (MWh)
            </p>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={450}>
          <AreaChart data={generationChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="tarih" stroke="#94a3b8" style={{ fontSize: '12px' }} />
            <YAxis stroke="#94a3b8" style={{ fontSize: '12px' }} label={{ value: 'Üretim (MWh)', angle: -90, position: 'insideLeft', fill: '#64748b' }} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
              formatter={(value: any) => `${value.toLocaleString()} MWh`}
            />
            <Legend wrapperStyle={{ fontSize: '13px' }} />
            <Area type="monotone" dataKey="Güneş" stackId="1" stroke={COLORS['Güneş']} fill={COLORS['Güneş']} />
            <Area type="monotone" dataKey="Rüzgar" stackId="1" stroke={COLORS['Rüzgar']} fill={COLORS['Rüzgar']} />
            <Area type="monotone" dataKey="Hidro" stackId="1" stroke={COLORS['Hidro']} fill={COLORS['Hidro']} />
            <Area type="monotone" dataKey="Doğalgaz" stackId="1" stroke={COLORS['Doğalgaz']} fill={COLORS['Doğalgaz']} />
            <Area type="monotone" dataKey="Linyit" stackId="1" stroke={COLORS['Linyit']} fill={COLORS['Linyit']} />
            <Area type="monotone" dataKey="Jeotermal" stackId="1" stroke={COLORS['Jeotermal']} fill={COLORS['Jeotermal']} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Secondary Charts */}
      <div className="charts-grid-secondary">
        {/* Toplam Üretim Trendi - Tam Genişlik */}
        <div className="chart-card" style={{ gridColumn: 'span 3' }}>
          <h3>Toplam Uretim Trendi</h3>
          <p className="chart-subtitle">Günlük toplam elektrik üretimi</p>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={totalGeneration}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="tarih" stroke="#94a3b8" style={{ fontSize: '12px' }} />
              <YAxis stroke="#94a3b8" style={{ fontSize: '12px' }} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                formatter={(value: any) => [`${value.toLocaleString()} MWh`, 'Toplam Üretim']}
              />
              <Line type="monotone" dataKey="toplam" stroke="#10b981" strokeWidth={3} dot={{ fill: '#10b981', r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Kaynak Payları - Pie Chart */}
        <div className="chart-card" style={{ gridColumn: 'span 3' }}>
          <h3>Ortalama Kaynak Paylari</h3>
          <p className="chart-subtitle">Son 7 günün ortalaması</p>
          <ResponsiveContainer width="100%" height={350}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} %${(percent * 100).toFixed(0)}`}
                outerRadius={130}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[entry.name as keyof typeof COLORS]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                formatter={(value: any) => `${value.toLocaleString()} MWh`}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Her kaynak için ayrı trend grafikleri - 3 sütun, 2 satır */}
        {sourcesTrend.map(source => (
          <div key={source.name} className="chart-card">
            <h3>{source.name} Trendi</h3>
            <p className="chart-subtitle">Günlük ortalama üretim</p>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={source.data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="tarih" stroke="#94a3b8" style={{ fontSize: '10px' }} />
                <YAxis stroke="#94a3b8" style={{ fontSize: '11px' }} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#f1f5f9' }}
                  formatter={(value: any) => [`${value.toLocaleString()} MWh`, source.name]}
                />
                <Bar dataKey="değer" fill={source.color} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ))}
      </div>
    </div>
  );
}
