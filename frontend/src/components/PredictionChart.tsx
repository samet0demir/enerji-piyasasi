import { Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, ComposedChart } from 'recharts';

interface PredictionData {
  date: string;
  predicted_price: number;
  lower_bound: number;
  upper_bound: number;
}

interface Props {
  data: PredictionData[];
}

export default function PredictionChart({ data }: Props) {
  const chartData = data.map(item => ({
    date: item.date.split(' ')[0],
    hour: item.date.split(' ')[1],
    predicted: Math.round(item.predicted_price),
    lower: Math.round(item.lower_bound),
    upper: Math.round(item.upper_bound)
  }));

  // Günlük ortalama al (24 saatlik veriyi grupla)
  const dailyData = chartData.reduce((acc: any[], item, index) => {
    const dayIndex = Math.floor(index / 24);
    if (!acc[dayIndex]) {
      acc[dayIndex] = {
        date: item.date,
        predicted: 0,
        lower: 0,
        upper: 0,
        count: 0
      };
    }
    acc[dayIndex].predicted += item.predicted;
    acc[dayIndex].lower += item.lower;
    acc[dayIndex].upper += item.upper;
    acc[dayIndex].count += 1;
    return acc;
  }, []).map(day => ({
    date: day.date,
    predicted: Math.round(day.predicted / day.count),
    lower: Math.round(day.lower / day.count),
    upper: Math.round(day.upper / day.count)
  }));

  return (
    <div className="chart-container">
      <h2>7 Günlük Fiyat Tahmini (Günlük Ortalama)</h2>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={dailyData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Area
            type="monotone"
            dataKey="upper"
            stroke="#82ca9d"
            fill="#82ca9d"
            fillOpacity={0.3}
            name="Üst Sınır"
          />
          <Area
            type="monotone"
            dataKey="lower"
            stroke="#82ca9d"
            fill="#ffffff"
            fillOpacity={1}
            name="Alt Sınır"
          />
          <Line
            type="monotone"
            dataKey="predicted"
            stroke="#ff7300"
            strokeWidth={3}
            name="Tahmin (TL/MWh)"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
