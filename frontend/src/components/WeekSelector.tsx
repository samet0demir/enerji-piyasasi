import { useEffect, useState } from 'react';
import { api } from '../services/api';

interface Week {
  week_start: string;
  week_end: string;
  is_complete: boolean;
  total_predictions: number;
  completed_predictions: number;
  completion_percentage: number;
  retrospective?: boolean;
  generation_count?: number;
  consumption_count?: number;
  performance: {
    mape: number;
    mae: number;
    rmse: number;
  } | null;
}

interface WeekSelectorProps {
  selectedWeek: string | null;
  onWeekChange: (weekStart: string) => void;
  availableFor?: 'forecasts' | 'generation' | 'consumption';
}

export default function WeekSelector({ selectedWeek, onWeekChange, availableFor = 'forecasts' }: WeekSelectorProps) {
  const [weeks, setWeeks] = useState<Week[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAvailableWeeks();
  }, [availableFor]);

  const fetchAvailableWeeks = async () => {
    try {
      setLoading(true);
      const available: Week[] = await api.getAvailableWeeks();
      const data = { success: true, weeks: available.filter(week =>
        availableFor === 'generation' ? (week.generation_count ?? 0) > 0 :
          availableFor === 'consumption' ? (week.consumption_count ?? 0) > 0 : true) };

      if (data.success) {
        setWeeks(data.weeks);
        // İlk haftayı otomatik seç (eğer henüz seçim yapılmadıysa)
        if ((!selectedWeek || !data.weeks.some(week => week.week_start === selectedWeek)) && data.weeks.length > 0) {
          onWeekChange(data.weeks[0].week_start);
        }
      } else {
        setError('Haftalar yüklenemedi');
      }
    } catch (err) {
      setError('Sunucu hatası');
      console.error('Failed to fetch weeks:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDateRange = (start: string, end: string) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const months = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];

    if (startDate.getMonth() === endDate.getMonth()) {
      return `${startDate.getDate()}-${endDate.getDate()} ${months[startDate.getMonth()]}`;
    } else {
      return `${startDate.getDate()} ${months[startDate.getMonth()]} - ${endDate.getDate()} ${months[endDate.getMonth()]}`;
    }
  };

  if (loading) {
    return (
      <div className="week-selector-container">
        <span className="week-selector-label">Yükleniyor...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="week-selector-container">
        <span className="week-selector-error">{error}</span>
      </div>
    );
  }

  if (weeks.length === 0) {
    return <div className="week-selector-container">Bu analiz için veri bulunan hafta yok.</div>;
  }

  return (
    <div className="week-selector-container">
      <label htmlFor="week-select" className="week-selector-label">
        Hafta Seçin:
      </label>
      <select
        id="week-select"
        className="week-selector-dropdown"
        value={selectedWeek || ''}
        onChange={(e) => onWeekChange(e.target.value || null as any)}
      >
        {weeks.map((week) => (
          <option key={week.week_start} value={week.week_start}>
            {formatDateRange(week.week_start, week.week_end)}
            {availableFor === 'forecasts' && week.retrospective && ' (Geriye dönük tahmin)'}
            {availableFor === 'forecasts' && !week.is_complete && ` (Devam ediyor...)`}
          </option>
        ))}
      </select>
    </div>
  );
}
