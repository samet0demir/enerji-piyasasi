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
}

export type ComparisonData = {
  datetime: string;
  predicted: number;
  actual: number;
  error: number;
  error_percent: number;
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

export const api = {
  async getForecasts(): Promise<ForecastsResponse> {
    try {
      const response = await axios.get(FORECASTS_JSON);
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
        hour: new Date(item.datetime).getHours().toString(),
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
        hour: new Date(item.datetime).getHours().toString(),
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
            actual: item.actual_price
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
    } catch (error) {
      console.error('Error fetching week data:', error);
      throw new Error('Hafta verileri yüklenemedi');
    }
  },

  async getWeeklyPerformance(): Promise<WeeklyPerformance[]> {
    try {
      const response = await axios.get(`${API_BASE}/weekly-performance`);
      return response.data.data;
    } catch (error) {
      console.error('Error fetching weekly performance:', error);
      return [];
    }
  }
};
