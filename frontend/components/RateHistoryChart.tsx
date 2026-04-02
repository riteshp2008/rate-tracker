"use client";

import React, { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { RateHistory } from "@/lib/api";
import { format, parseISO } from "date-fns";

interface RateHistoryChartProps {
  data: RateHistory[];
  loading?: boolean;
  title?: string;
}

/**
 * 30-day historical rate chart using Recharts.
 * Displays rate trends over time for visual analysis.
 */
export function RateHistoryChart({
  data,
  loading = false,
  title = "30-Day Rate History",
}: RateHistoryChartProps) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    return data
      .sort(
        (a, b) =>
          new Date(a.effective_date).getTime() -
          new Date(b.effective_date).getTime(),
      )
      .map((item) => ({
        date: format(parseISO(item.effective_date), "MMM dd"),
        rate: parseFloat(item.rate_value),
        fullDate: item.effective_date,
      }));
  }, [data]);

  if (loading) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading chart...</span>
        </div>
      </div>
    );
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="text-center py-12 text-gray-500">
          <p>No historical data available</p>
        </div>
      </div>
    );
  }

  const minRate = Math.min(...chartData.map((d) => d.rate));
  const maxRate = Math.max(...chartData.map((d) => d.rate));
  const avgRate =
    chartData.reduce((sum, d) => sum + d.rate, 0) / chartData.length;

  return (
    <div className="card">
      <div className="mb-4">
        <h3 className="text-lg font-semibold">{title}</h3>
        <div className="mt-2 grid grid-cols-3 gap-4 text-sm">
          <div className="bg-blue-50 p-2 rounded">
            <span className="text-gray-600">Min</span>
            <p className="font-semibold text-blue-600">{minRate.toFixed(4)}%</p>
          </div>
          <div className="bg-green-50 p-2 rounded">
            <span className="text-gray-600">Avg</span>
            <p className="font-semibold text-green-600">
              {avgRate.toFixed(4)}%
            </p>
          </div>
          <div className="bg-orange-50 p-2 rounded">
            <span className="text-gray-600">Max</span>
            <p className="font-semibold text-orange-600">
              {maxRate.toFixed(4)}%
            </p>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis domain={["dataMin - 0.1", "dataMax + 0.1"]} />
          <Tooltip
            formatter={(value: number) => value.toFixed(4) + "%"}
            labelFormatter={(label) => "Date: " + label}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="rate"
            stroke="#2563eb"
            dot={{ fill: "#2563eb", r: 4 }}
            activeDot={{ r: 6 }}
            name="Rate (%)"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
