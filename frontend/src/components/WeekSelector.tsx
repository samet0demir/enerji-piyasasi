import { useEffect, useState } from 'react';

interface Week {
  week_start: string;
  week_end: string;
  is_complete: boolean;
  total_predictions: number;
  completed_predictions: number;
  completion_percentage: number;
  performance: {
    mape: number;
    mae: number;
    rmse: number;
  } | null;
}

interface WeekSelectorProps {
  selectedWeek: string | null;
  onWeekChange: (weekStart: string) => void;
}

export default function WeekSelector({ selectedWeek, onWeekChange }: WeekSelectorProps) {
  const [weeks, setWeeks] = useState<Week[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAvailableWeeks();
  }, []);

  const fetchAvailableWeeks = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:5001/api/weeks/available');
      const data = await response.json();

      if (data.success) {
        setWeeks(data.weeks);

        // Eğer hiç seçili hafta yoksa, en son tamamlanmış haftayı seç
        if (!selectedWeek && data.weeks.length > 0) {
          const lastCompleteWeek = data.weeks.find((w: Week) => w.is_complete);
          if (lastCompleteWeek) {
            onWeekChange(lastCompleteWeek.week_start);
          } else {
            // Tamamlanmış hafta yoksa en eskisini seç
            onWeekChange(data.weeks[data.weeks.length - 1].week_start);
          }
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
    const months = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];

    if (startDate.getMonth() === endDate.getMonth()) {
      return `${startDate.getDate()}-${endDate.getDate()} ${months[startDate.getMonth()]}`;
    } else {
      return `${startDate.getDate()} ${months[startDate.getMonth()]}-${endDate.getDate()} ${months[endDate.getMonth()]}`;
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

  return (
    <div className="week-selector-container">
      <label htmlFor="week-select" className="week-selector-label">
        Hafta Seçin:
      </label>
      <select
        id="week-select"
        className="week-selector-dropdown"
        value={selectedWeek || ''}
        onChange={(e) => onWeekChange(e.target.value)}
      >
        {weeks.map((week) => (
          <option key={week.week_start} value={week.week_start}>
            {formatDateRange(week.week_start, week.week_end)}
            {!week.is_complete && ` (Devam ediyor... %${week.completion_percentage})`}
          </option>
        ))}
      </select>
    </div>
  );
}
