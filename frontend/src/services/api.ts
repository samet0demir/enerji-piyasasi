import axios from 'axios';

// Static JSON path (served from backend/public or deployed static hosting)
const FORECASTS_JSON = '/forecasts.json';

// Type definitions
export type ForecastData = {
  datetime: string;
  predicted: number;
  actual?: number | null;
  lower_bound?: number;
  upper_bound?: number;
  lower?: number;
  upper?: number;
  prophet?: number;
  lstm?: number;
  xgboost?: number;
  // Database model components
  prophet_component?: number | null;
  xgboost_component?: number | null;
  lstm_component?: number | null;
}

export type ComparisonData = {
  datetime: string;
  predicted: number;
  actual: number;
  error: number;
  error_percent: number | null;
}

export type WeeklyPerformance = {
  week_start: string;
  week_end: string;
  mape: number;
  mae: number;
  rmse: number;
  total_predictions: number;
}

export type ForecastsResponse = {
  generated_at: string;
  current_week: {
    start: string;
    end: string;
    forecasts: ForecastData[];
  };
  last_week_performance: WeeklyPerformance | null;
  last_week_comparison: ComparisonData[];
  historical_trend: WeeklyPerformance[];
}

export type GenerationData = {
  date: string;
  hour: string;
  total: number;
  solar: number;
  wind: number;
  hydro: number;
  natural_gas: number;
  lignite: number;
  geothermal: number;
  biomass: number;
}

export type ConsumptionData = {
  date: string;
  hour: string;
  consumption: number;
}

// API functions
const API_BASE = 'http://localhost:5001/api';

type HistoryWeek = {
  week_start: string;
  week_end: string;
  forecasts: (ForecastData & { error: number; error_percent: number | null })[];
  performance: WeeklyPerformance | null;
  provenance: { kind: string } | null;
};

async function loadHistory(): Promise<{ generated_at: string; weeks: HistoryWeek[] }> {
  const response = await axios.get(`/forecast-history.json?t=${Date.now()}`);
  return response.data;
}

export const api = {
  async getAvailableWeeks() {
    try {
      const response = await axios.get(`${API_BASE}/weeks/available`);
      if (!response.data.success) throw new Error('Haftalar yüklenemedi');
      return response.data.weeks;
    } catch {
      const history = await loadHistory();
      return history.weeks.map(week => {
        const completed = week.forecasts.filter(row => row.actual != null).length;
        return {
          week_start: week.week_start, week_end: week.week_end,
          total_predictions: week.forecasts.length, completed_predictions: completed,
          is_complete: completed === week.forecasts.length,
          completion_percentage: Math.round(completed / week.forecasts.length * 100),
          performance: week.performance,
          retrospective: week.provenance?.kind === 'retrospective'
        };
      });
    }
  },
  async getForecasts(): Promise<ForecastsResponse> {
    try {
      const timestamp = new Date().getTime();
      const response = await axios.get(`${FORECASTS_JSON}?t=${timestamp}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching forecasts:', error);
      throw new Error('Tahmin verileri yüklenemedi. Lütfen backend\'in çalıştığından emin olun.');
    }
  },

  async getGeneration(): Promise<GenerationData[]> {
    try {
      const response = await axios.get(`${API_BASE}/generation/recent`);
      return response.data.generation;
    } catch (error) {
      console.error('Error fetching generation:', error);
      return [];
    }
  },

  async getGenerationByWeek(weekStart: string): Promise<GenerationData[]> {
    try {
      const response = await axios.get(`${API_BASE}/weeks/${weekStart}/data`);
      // Generation verisini döndür
      return response.data.generation.data.map((item: any) => ({
        date: item.datetime,
        hour: item.datetime.slice(11, 16),
        total: item.total,
        solar: item.solar,
        wind: item.wind,
        hydro: item.hydro,
        natural_gas: item.natural_gas,
        lignite: item.lignite,
        geothermal: item.geothermal,
        biomass: item.biomass
      }));
    } catch (error) {
      console.error('Error fetching generation by week:', error);
      return [];
    }
  },

  async getConsumption(): Promise<ConsumptionData[]> {
    try {
      const response = await axios.get(`${API_BASE}/consumption/recent`);
      return response.data.consumption;
    } catch (error) {
      console.error('Error fetching consumption:', error);
      return [];
    }
  },

  async getConsumptionByWeek(weekStart: string): Promise<ConsumptionData[]> {
    try {
      const response = await axios.get(`${API_BASE}/weeks/${weekStart}/data`);
      // Consumption verisini döndür
      return response.data.consumption.data.map((item: any) => ({
        date: item.datetime,
        hour: item.datetime.slice(11, 16),
        consumption: item.consumption
      }));
    } catch (error) {
      console.error('Error fetching consumption by week:', error);
      return [];
    }
  },

  async getWeekData(weekStart: string): Promise<ForecastsResponse> {
    try {
      const response = await axios.get(`${API_BASE}/weeks/${weekStart}/data`);
      const data = response.data;

      // Backend'den gelen veriyi ForecastsResponse formatına çevir
      const forecastsResponse: ForecastsResponse = {
        generated_at: new Date().toISOString(),
        current_week: {
          start: data.week.start,
          end: data.week.end,
          forecasts: data.mcp.data.map((item: any) => ({
            datetime: item.datetime,
            predicted: item.predicted_price,
            actual: item.actual_price,
            // Model bileşenleri (veritabanından)
            prophet: item.prophet_component,
            xgboost: item.xgboost_component,
            lstm: item.lstm_component
          }))
        },
        last_week_performance: data.performance ? {
          week_start: data.week.start,
          week_end: data.week.end,
          mape: data.performance.mape,
          mae: data.performance.mae,
          rmse: data.performance.rmse,
          total_predictions: data.performance.total_predictions
        } : null,
        last_week_comparison: data.mcp.data
          .filter((item: any) => item.actual_price !== null)
          .map((item: any) => ({
            datetime: item.datetime,
            predicted: item.predicted_price,
            actual: item.actual_price,
            error: item.absolute_error,
            error_percent: item.percentage_error
          })),
        historical_trend: [] // Bu veri haftaya özgü olduğu için boş bırakıyoruz
      };

      return forecastsResponse;

    } catch (error: any) {
      console.error('Error fetching week data:', error);
      try {
        const history = await loadHistory();
        const week = history.weeks.find(item => item.week_start === weekStart);
        if (!week) throw new Error('Arşivde hafta bulunamadı');
        return {
          generated_at: history.generated_at,
          current_week: { start: week.week_start, end: week.week_end, forecasts: week.forecasts },
          last_week_performance: week.performance,
          last_week_comparison: week.forecasts.filter(row => row.actual != null).map(row => ({
            datetime: row.datetime, predicted: row.predicted, actual: row.actual!,
            error: row.error, error_percent: row.error_percent
          })),
          historical_trend: history.weeks.flatMap(item => item.performance ? [item.performance] : [])
        };
      } catch {
        // Report the original API failure if the published archive is unavailable too.
      }
      const errorMessage = error.response?.data?.message || error.message || 'Bilinmeyen hata';
      throw new Error(`Hafta verileri yüklenemedi: ${errorMessage}`);
    }
  },

  async getWeeklyPerformance(): Promise<WeeklyPerformance[]> {
    try {
      const response = await axios.get(`${API_BASE}/weekly-performance`);
      return response.data.data;
    } catch (error) {
      console.error('Error fetching weekly performance:', error);
      try {
        const history = await loadHistory();
        return history.weeks.flatMap(week => week.performance ? [week.performance] : []);
      } catch {
        return [];
      }
    }
  }
};
