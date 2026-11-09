import React from "react";
import { DailyAnalyticsBucket } from "@/lib/api";

interface VolumeBarChartProps {
  buckets: DailyAnalyticsBucket[];
}

export function VolumeBarChart({ buckets }: VolumeBarChartProps) {
  if (buckets.length === 0) {
    return (
      <div
        data-testid="volume-bar-chart-empty"
        className="flex h-56 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-white text-xs text-slate-500 italic shadow-xs"
      >
        No execution volume recorded for this time window.
      </div>
    );
  }

  const width = 600;
  const height = 180;
  const paddingX = 40;
  const paddingTop = 25;
  const paddingBottom = 35;

  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingTop - paddingBottom;

  const maxVolume = Math.max(...buckets.map((b) => b.evaluation_count), 4);
  const barWidth = Math.max(12, Math.min(36, chartWidth / (buckets.length * 1.5)));

  return (
    <div
      data-testid="volume-bar-chart"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs space-y-3"
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900">Daily Evaluation Throughput</h3>
          <p className="text-xs text-slate-500">Total number of agent trace evaluations executed per day</p>
        </div>
      </div>

      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto min-w-[500px]"
          aria-label="Evaluation Volume Bar Chart"
        >
          {/* Base horizontal axis */}
          <line
            x1={paddingX}
            y1={height - paddingBottom}
            x2={width - paddingX}
            y2={height - paddingBottom}
            stroke="#e2e8f0"
            strokeWidth="1"
          />

          {buckets.map((b, i) => {
            const xCenter =
              buckets.length === 1
                ? width / 2
                : paddingX + (i / (buckets.length - 1)) * chartWidth;
            const barX = xCenter - barWidth / 2;
            const barH = (b.evaluation_count / maxVolume) * chartHeight;
            const barY = height - paddingBottom - barH;

            return (
              <g key={`bar-${b.date}`}>
                {/* Bar */}
                <rect
                  x={barX}
                  y={barY}
                  width={barWidth}
                  height={barH}
                  rx="3"
                  className="fill-blue-600 hover:fill-blue-700 transition"
                />
                {/* Value on top */}
                <text
                  x={xCenter}
                  y={barY - 5}
                  textAnchor="middle"
                  fontSize="9"
                  fontWeight="bold"
                  fill="#0f172a"
                  fontFamily="monospace"
                >
                  {b.evaluation_count}
                </text>
                {/* Date on bottom */}
                <text
                  x={xCenter}
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
        </svg>
      </div>
    </div>
  );
}

