import React from "react";
import { DailyAnalyticsBucket } from "@/lib/api";

interface ScoreTrendChartProps {
  buckets: DailyAnalyticsBucket[];
}

export function ScoreTrendChart({ buckets }: ScoreTrendChartProps) {
  if (buckets.length === 0) {
    return (
      <div
        data-testid="score-trend-chart-empty"
        className="flex h-56 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white text-xs text-slate-500 italic shadow-xs"
      >
        No historical score data available for the selected time window.
      </div>
    );
  }

  const width = 600;
  const height = 220;
  const paddingX = 45;
  const paddingTop = 25;
  const paddingBottom = 40;

  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingTop - paddingBottom;

  // Map Y: 0..100 -> height
  const getY = (score: number) => {
    const clamped = Math.max(0, Math.min(100, score));
    return paddingTop + chartHeight - (clamped / 100) * chartHeight;
  };

  // Map X: index -> width
  const getX = (index: number) => {
    if (buckets.length === 1) return paddingX + chartWidth / 2;
    return paddingX + (index / (buckets.length - 1)) * chartWidth;
  };

  const points = buckets.map((b, i) => `${getX(i)},${getY(b.average_score)}`).join(" ");

  // Baseline 80 threshold
  const y80 = getY(80);

  return (
    <div
      data-testid="score-trend-chart"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-3"
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900">Score Trajectory Over Time</h3>
          <p className="text-xs text-slate-500">Mean overall execution score across chronological date buckets</p>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-slate-500">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-600" /> Average Score
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-0.5 w-3 border-t border-dashed border-emerald-600" /> Pass Baseline (80.0)
          </span>
        </div>
      </div>

      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto min-w-[500px]"
          aria-label="Score Trend Line Chart"
        >
          {/* Horizontal gridlines */}
          {[0, 25, 50, 75, 100].map((val) => {
            const y = getY(val);
            return (
              <g key={`grid-${val}`}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={width - paddingX}
                  y2={y}
                  stroke="#e2e8f0"
                  strokeWidth="1"
                />
                <text
                  x={paddingX - 8}
                  y={y + 3}
                  textAnchor="end"
                  fontSize="9"
                  fill="#64748b"
                  fontFamily="monospace"
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* 80 pass baseline */}
          <line
            x1={paddingX}
            y1={y80}
            x2={width - paddingX}
            y2={y80}
            stroke="#16a34a"
            strokeWidth="1.2"
            strokeDasharray="4 4"
            opacity="0.8"
          />

          {/* Area fill */}
          {buckets.length > 1 && (
            <polygon
              points={`${getX(0)},${paddingTop + chartHeight} ${points} ${getX(
                buckets.length - 1
              )},${paddingTop + chartHeight}`}
              fill="url(#scoreGradient)"
              opacity="0.15"
            />
          )}

          {/* Trend Polyline */}
          <polyline
            points={points}
            fill="none"
            stroke="#16a34a"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Interactive point markers */}
          {buckets.map((b, i) => {
            const cx = getX(i);
            const cy = getY(b.average_score);
            return (
              <g key={`point-${b.date}`}>
                <circle
                  cx={cx}
                  cy={cy}
                  r="4"
                  fill="#ffffff"
                  stroke="#16a34a"
                  strokeWidth="2"
                  className="transition hover:r-6"
                />
                <text
                  x={cx}
                  y={cy - 8}
                  textAnchor="middle"
                  fontSize="9"
                  fontWeight="bold"
                  fill="#0f172a"
                  fontFamily="monospace"
                >
                  {b.average_score.toFixed(1)}
                </text>
                {/* Date label */}
                <text
                  x={cx}
                  y={height - 12}
                  textAnchor="middle"
                  fontSize="9"
                  fill="#64748b"
                  fontFamily="monospace"
                >
                  {b.date.slice(5)}
                </text>
              </g>
            );
          })}

          {/* Linear gradient */}
          <defs>
            <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#16a34a" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#16a34a" stopOpacity="0.0" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>
  );
}

