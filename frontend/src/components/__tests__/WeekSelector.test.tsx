import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import WeekSelector from '../WeekSelector';
import { Production } from '../../pages/Production';
import { Consumption } from '../../pages/Consumption';
import { api } from '../../services/api';

vi.mock('../../services/api', () => ({ api: {
  getAvailableWeeks: vi.fn(), getGeneration: vi.fn(), getGenerationByWeek: vi.fn(),
  getConsumption: vi.fn(), getConsumptionByWeek: vi.fn()
} }));

const weeks = [
  { week_start: '2026-10-05', week_end: '2026-10-11', generation_count: 0, consumption_count: 0 },
  { week_start: '2026-09-28', week_end: '2026-10-04', generation_count: 168, consumption_count: 168 }
];

describe('analysis week selection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getAvailableWeeks).mockResolvedValue(weeks);
    vi.mocked(api.getGeneration).mockResolvedValue([]);
    vi.mocked(api.getGenerationByWeek).mockResolvedValue([]);
    vi.mocked(api.getConsumption).mockResolvedValue([]);
    vi.mocked(api.getConsumptionByWeek).mockResolvedValue([]);
  });
  afterEach(cleanup);

  it('excludes forecast-only weeks from production analysis', async () => {
    const change = vi.fn();
    render(<WeekSelector selectedWeek={null} onWeekChange={change} availableFor="generation" />);
    await waitFor(() => expect(change).toHaveBeenCalledWith('2026-09-28'));
    expect(screen.getAllByRole('option')).toHaveLength(1);
  });

  it('preserves the current week for the forecast dashboard', async () => {
    const change = vi.fn();
    render(<WeekSelector selectedWeek={null} onWeekChange={change} />);
    await waitFor(() => expect(change).toHaveBeenCalledWith('2026-10-05'));
    expect(screen.getAllByRole('option')).toHaveLength(2);
  });

  it('keeps production week selection accessible when data is empty', async () => {
    render(<Production />);
    await waitFor(() => expect(api.getGenerationByWeek).toHaveBeenCalledWith('2026-09-28'));
    expect(await screen.findByRole('combobox')).toBeInTheDocument();
    expect(await screen.findByText('Üretim verileri yüklenemedi')).toBeInTheDocument();
  });

  it('keeps consumption week selection accessible when data is empty', async () => {
    render(<Consumption />);
    await waitFor(() => expect(api.getConsumptionByWeek).toHaveBeenCalledWith('2026-09-28'));
    expect(await screen.findByRole('combobox')).toBeInTheDocument();
    expect(await screen.findByText('Tüketim verileri yüklenemedi')).toBeInTheDocument();
  });
});
