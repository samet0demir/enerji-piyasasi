import { describe, it, expect, beforeEach, vi } from 'vitest';
import axios from 'axios';
import { api } from '../api';
import type { ForecastsResponse, GenerationData, ConsumptionData } from '../api';

// Mock axios
vi.mock('axios');
const mockedAxios = axios as any;

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getForecasts', () => {
    it('should fetch forecasts successfully', async () => {
      const mockResponse: ForecastsResponse = {
        generated_at: '2025-10-28T12:00:00Z',
        current_week: {
          start: '2025-10-28',
          end: '2025-11-03',
          forecasts: [
            {
              datetime: '2025-10-28 00:00',
              predicted: 2500.50,
              actual: null,
              lower_bound: 2300,
              upper_bound: 2700
            },
            {
              datetime: '2025-10-28 01:00',
              predicted: 2400.00,
              actual: null,
              lower_bound: 2200,
              upper_bound: 2600
            }
          ]
        },
        last_week_performance: {
          week_start: '2025-10-21',
          week_end: '2025-10-27',
          mape: 12.5,
          mae: 150.3,
          rmse: 200.8,
          total_predictions: 168
        },
        last_week_comparison: [
          {
            datetime: '2025-10-21 00:00',
            predicted: 2450,
            actual: 2500,
            error: -50,
            error_percent: -2.0
          }
        ],
        historical_trend: [
          {
            week_start: '2025-10-14',
            week_end: '2025-10-20',
            mape: 13.2,
            mae: 160,
            rmse: 210,
            total_predictions: 168
          }
        ]
      };

      mockedAxios.get = vi.fn().mockResolvedValue({ data: mockResponse });

      const result = await api.getForecasts();

      expect(result).toEqual(mockResponse);
      expect(mockedAxios.get).toHaveBeenCalledWith(expect.stringMatching(/^\/forecasts\.json\?t=\d+$/));
      expect(result.current_week.forecasts).toHaveLength(2);
      expect(result.last_week_performance?.mape).toBe(12.5);
    });

    it('should throw error when forecast fetch fails', async () => {
      const errorMessage = 'Network Error';
      mockedAxios.get = vi.fn().mockRejectedValue(new Error(errorMessage));

      // Suppress console.error during test
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      await expect(api.getForecasts()).rejects.toThrow(
        'Tahmin verileri yüklenemedi. Lütfen backend\'in çalıştığından emin olun.'
      );

      expect(consoleError).toHaveBeenCalledWith('Error fetching forecasts:', expect.any(Error));
      consoleError.mockRestore();
    });

    it('should handle null last_week_performance', async () => {
      const mockResponse: ForecastsResponse = {
        generated_at: '2025-10-28T12:00:00Z',
        current_week: {
          start: '2025-10-28',
          end: '2025-11-03',
          forecasts: []
        },
        last_week_performance: null,
        last_week_comparison: [],
        historical_trend: []
      };

      mockedAxios.get = vi.fn().mockResolvedValue({ data: mockResponse });

      const result = await api.getForecasts();

      expect(result.last_week_performance).toBeNull();
    });
  });

  describe('getGeneration', () => {
    it('should fetch generation data successfully', async () => {
      const mockGeneration: GenerationData[] = [
        {
          date: '2025-10-28T00:00:00+03:00',
          hour: '00:00',
          total: 35000,
          solar: 0,
          wind: 5000,
          hydro: 8000,
          natural_gas: 12000,
          lignite: 7000,
          geothermal: 3000,
          biomass: 0
        },
        {
          date: '2025-10-28T00:00:00+03:00',
          hour: '01:00',
          total: 33500,
          solar: 0,
          wind: 4800,
          hydro: 7500,
          natural_gas: 11500,
          lignite: 6800,
          geothermal: 2900,
          biomass: 0
        }
      ];

      mockedAxios.get = vi.fn().mockResolvedValue({
        data: { generation: mockGeneration }
      });

      const result = await api.getGeneration();

      expect(result).toEqual(mockGeneration);
      expect(mockedAxios.get).toHaveBeenCalledWith('http://localhost:5001/api/generation/recent');
      expect(result).toHaveLength(2);
      expect(result[0].total).toBe(35000);
    });

    it('should return empty array when generation fetch fails', async () => {
      mockedAxios.get = vi.fn().mockRejectedValue(new Error('Network Error'));

      // Suppress console.error during test
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const result = await api.getGeneration();

      expect(result).toEqual([]);
      expect(consoleError).toHaveBeenCalledWith('Error fetching generation:', expect.any(Error));
      consoleError.mockRestore();
    });

    it('should handle empty generation data', async () => {
      mockedAxios.get = vi.fn().mockResolvedValue({
        data: { generation: [] }
      });

      const result = await api.getGeneration();

      expect(result).toEqual([]);
      expect(result).toHaveLength(0);
    });

    it('should correctly parse generation data structure', async () => {
      const mockData: GenerationData[] = [
        {
          date: '2025-10-28T00:00:00+03:00',
          hour: '12:00',
          total: 40000,
          solar: 8000,
          wind: 6000,
          hydro: 9000,
          natural_gas: 10000,
          lignite: 5000,
          geothermal: 2000,
          biomass: 0
        }
      ];

      mockedAxios.get = vi.fn().mockResolvedValue({
        data: { generation: mockData }
      });

      const result = await api.getGeneration();

      expect(result[0].solar).toBe(8000);
      expect(result[0].wind).toBe(6000);
      expect(result[0].hydro).toBe(9000);
      expect(result[0].natural_gas).toBe(10000);
    });
  });

  describe('getConsumption', () => {
    it('should fetch consumption data successfully', async () => {
      const mockConsumption: ConsumptionData[] = [
        {
          date: '2025-10-28T00:00:00+03:00',
          hour: '00:00',
          consumption: 32000
        },
        {
          date: '2025-10-28T00:00:00+03:00',
          hour: '01:00',
          consumption: 31500
        },
        {
          date: '2025-10-28T00:00:00+03:00',
          hour: '02:00',
          consumption: 30800
        }
      ];

      mockedAxios.get = vi.fn().mockResolvedValue({
        data: { consumption: mockConsumption }
      });

      const result = await api.getConsumption();

      expect(result).toEqual(mockConsumption);
      expect(mockedAxios.get).toHaveBeenCalledWith('http://localhost:5001/api/consumption/recent');
      expect(result).toHaveLength(3);
      expect(result[0].consumption).toBe(32000);
    });

    it('should return empty array when consumption fetch fails', async () => {
      mockedAxios.get = vi.fn().mockRejectedValue(new Error('Network Error'));

      // Suppress console.error during test
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const result = await api.getConsumption();

      expect(result).toEqual([]);
      expect(consoleError).toHaveBeenCalledWith('Error fetching consumption:', expect.any(Error));
      consoleError.mockRestore();
    });

    it('should handle empty consumption data', async () => {
      mockedAxios.get = vi.fn().mockResolvedValue({
        data: { consumption: [] }
      });

      const result = await api.getConsumption();

      expect(result).toEqual([]);
      expect(result).toHaveLength(0);
    });

    it('should correctly parse consumption data with various values', async () => {
      const mockData: ConsumptionData[] = [
        { date: '2025-10-28T00:00:00+03:00', hour: '06:00', consumption: 28000 },
        { date: '2025-10-28T00:00:00+03:00', hour: '12:00', consumption: 35000 },
        { date: '2025-10-28T00:00:00+03:00', hour: '18:00', consumption: 38000 },
        { date: '2025-10-28T00:00:00+03:00', hour: '23:00', consumption: 33000 }
      ];

      mockedAxios.get = vi.fn().mockResolvedValue({
        data: { consumption: mockData }
      });

      const result = await api.getConsumption();

      expect(result).toHaveLength(4);
      expect(result[1].consumption).toBe(35000); // 12:00
      expect(result[2].consumption).toBe(38000); // Peak at 18:00
    });
  });

  describe('Error Handling', () => {
    it('should handle axios timeout errors', async () => {
      const timeoutError = {
        code: 'ECONNABORTED',
        message: 'timeout of 5000ms exceeded'
      };
      mockedAxios.get = vi.fn().mockRejectedValue(timeoutError);

      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const result = await api.getGeneration();
      expect(result).toEqual([]);

      consoleError.mockRestore();
    });

    it('should handle 404 errors gracefully', async () => {
      const error404 = {
        response: { status: 404, statusText: 'Not Found' }
      };
      mockedAxios.get = vi.fn().mockRejectedValue(error404);

      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      const result = await api.getConsumption();
      expect(result).toEqual([]);

      consoleError.mockRestore();
    });

    it('should handle 500 server errors', async () => {
      const error500 = {
        response: { status: 500, statusText: 'Internal Server Error' }
      };
      mockedAxios.get = vi.fn().mockRejectedValue(error500);

      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

      await expect(api.getForecasts()).rejects.toThrow();

      consoleError.mockRestore();
    });
  });

  describe('API Endpoints', () => {
    it('should use correct endpoint for forecasts', async () => {
      mockedAxios.get = vi.fn().mockResolvedValue({
        data: {
          generated_at: '2025-10-28T12:00:00Z',
          current_week: { start: '', end: '', forecasts: [] },
          last_week_performance: null,
          last_week_comparison: [],
          historical_trend: []
        }
      });

      await api.getForecasts();

      expect(mockedAxios.get).toHaveBeenCalledWith(expect.stringMatching(/^\/forecasts\.json\?t=\d+$/));
    });

    it('should use correct endpoint for generation', async () => {
      mockedAxios.get = vi.fn().mockResolvedValue({
        data: { generation: [] }
      });

      await api.getGeneration();

      expect(mockedAxios.get).toHaveBeenCalledWith('http://localhost:5001/api/generation/recent');
    });

    it('should use correct endpoint for consumption', async () => {
      mockedAxios.get = vi.fn().mockResolvedValue({
        data: { consumption: [] }
      });

      await api.getConsumption();

      expect(mockedAxios.get).toHaveBeenCalledWith('http://localhost:5001/api/consumption/recent');
    });
  });
});
