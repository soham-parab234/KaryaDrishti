import React, { useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Area,
} from 'recharts';
import type { MonthlyTrendData } from '../../types/lmis';
import { formatNumber, formatSignedNumber } from '../../utils/calculations';
import { Info, BarChart2, TrendingUp } from 'lucide-react';

interface DemandSupplyChartProps {
  data: MonthlyTrendData[];
}

interface CustomTooltipProps {
  active?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload?: any[];
  label?: string;
  data: MonthlyTrendData[];
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label, data }) => {
  if (active && payload && payload.length) {
    const currentPoint = data.find((d) => d.period === label);
    const demandVal = payload.find((p: { dataKey: string }) => p.dataKey === 'documentedDemand')?.value ?? 0;
    const supplyVal = payload.find((p: { dataKey: string }) => p.dataKey === 'qualifiedSupply')?.value ?? 0;
    const gap = Number(demandVal) - Number(supplyVal);
    const isForecast = currentPoint?.isForecast;

    return (
      <div
        style={{
          backgroundColor: '#ffffff',
          border: '1px solid #d6d3d1',
          borderRadius: '4px',
          padding: '12px 14px',
          boxShadow: '0 2px 8px rgba(28, 25, 23, 0.08)',
          fontSize: '12px',
          minWidth: '220px',
        }}
      >
        <div style={{ fontWeight: 700, color: '#1c1917', marginBottom: '6px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>{label}</span>
          {isForecast && (
            <span style={{ fontSize: '10px', background: '#ffedd5', color: '#c2410c', padding: '1px 5px', borderRadius: '2px', fontWeight: 700 }}>
              BASELINE PROJECTION
            </span>
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ color: '#1e3a8a' }}>● Documented Demand:</span>
          <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{formatNumber(Number(demandVal))}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ color: '#0f766e' }}>● Qualified Supply:</span>
          <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{formatNumber(Number(supplyVal))}</span>
        </div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            paddingTop: '6px',
            borderTop: '1px dashed #e7e5e4',
            fontWeight: 700,
            color: gap > 0 ? '#c2410c' : gap < 0 ? '#4338ca' : '#15803d',
          }}
        >
          <span>Net Gap Signal:</span>
          <span style={{ fontFamily: 'monospace' }}>{formatSignedNumber(gap)}</span>
        </div>
        {isForecast && currentPoint?.uncertaintyLower && currentPoint?.uncertaintyUpper && (
          <div style={{ marginTop: '6px', fontSize: '11px', color: '#78716c', fontStyle: 'italic' }}>
            Uncertainty (90% Interval): {formatNumber(currentPoint.uncertaintyLower)} – {formatNumber(currentPoint.uncertaintyUpper)}
          </div>
        )}
        <div style={{ marginTop: '6px', fontSize: '10px', color: '#a8a29e', borderTop: '1px solid #f5f5f4', paddingTop: '4px' }}>
          Status: CALIBRATED BASELINE (SYNTHETIC)
        </div>
      </div>
    );
  }
  return null;
};

export const DemandSupplyChart: React.FC<DemandSupplyChartProps> = ({ data }) => {
  const [chartMode, setChartMode] = useState<'composed' | 'trend'>('composed');

  return (
    <section className="editorial-card" aria-label="Demand versus Supply Analysis Chart">
      <div className="editorial-card-header">
        <div className="editorial-heading-group" style={{ marginBottom: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h3>Demand Signal vs. Qualified Supply Trajectory</h3>
            <span className="badge badge-synthetic">CALIBRATED BASELINE</span>
          </div>
          <div className="heading-accent-bar" style={{ width: '28px', marginTop: '4px' }}></div>
          <p style={{ fontSize: '12.5px', marginTop: '4px' }}>
            12-month documented hiring signals (Nov 2025 – Oct 2026) with 3-month baseline moving-average projection.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className={`gov-btn ${chartMode === 'composed' ? 'gov-btn-primary' : 'gov-btn-outline'}`}
            onClick={() => setChartMode('composed')}
            title="Comparative Bar & Line View"
          >
            <BarChart2 size={13} />
            <span>Comparative View</span>
          </button>
          <button
            type="button"
            className={`gov-btn ${chartMode === 'trend' ? 'gov-btn-primary' : 'gov-btn-outline'}`}
            onClick={() => setChartMode('trend')}
            title="Continuous Trend Lines with Uncertainty Interval"
          >
            <TrendingUp size={13} />
            <span>Uncertainty Bands</span>
          </button>
        </div>
      </div>

      <div style={{ width: '100%', height: 320, marginTop: '8px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 15, right: 15, bottom: 15, left: 5 }}>
            <CartesianGrid strokeDasharray="2 2" stroke="#f0ebe1" vertical={false} />
            <XAxis
              dataKey="period"
              tick={{ fill: '#78716c', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#e7e5e4' }}
            />
            <YAxis
              tick={{ fill: '#78716c', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              domain={[3000, 5400]}
              tickFormatter={(v) => `${v}`}
            />
            <Tooltip content={<CustomTooltip data={data} />} />
            <Legend
              wrapperStyle={{ paddingTop: '8px', fontSize: '11.5px', color: '#44403c' }}
              iconType="circle"
            />

            {/* In trend mode, display uncertainty area for forecast periods */}
            {chartMode === 'trend' && (
              <Area
                type="monotone"
                dataKey="uncertaintyUpper"
                stroke="transparent"
                fill="#fef3c7"
                fillOpacity={0.7}
                name="Forecast Uncertainty (90% Interval)"
              />
            )}

            {/* Documented Demand */}
            {chartMode === 'composed' ? (
              <Bar
                dataKey="documentedDemand"
                fill="#1e3a8a"
                name="Documented Demand Signals (Postings)"
                radius={[2, 2, 0, 0]}
                maxBarSize={24}
              />
            ) : (
              <Line
                type="monotone"
                dataKey="documentedDemand"
                stroke="#1e3a8a"
                strokeWidth={2}
                dot={{ r: 2.5, fill: '#1e3a8a' }}
                name="Documented Demand Signals"
              />
            )}

            {/* Qualified Supply */}
            <Line
              type="monotone"
              dataKey="qualifiedSupply"
              stroke="#0f766e"
              strokeWidth={2}
              dot={{ r: 2.5, fill: '#0f766e' }}
              name="Qualified Supply Estimate"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11.5px', color: '#57534e', backgroundColor: '#fcfaf6', padding: '8px 12px', borderRadius: '4px', border: '1px solid #e7e5e4' }}>
        <Info size={14} style={{ color: '#c2410c', flexShrink: 0 }} />
        <span>
          <strong>Analytical Caveat:</strong> Demand represents documented employer postings across monitored online portals, not an exhaustive census of all economic vacancies. 
          Qualified supply is an estimated pool of plausibly available certified personnel, strictly separated from institutional training capacity.
        </span>
      </div>
    </section>
  );
};
