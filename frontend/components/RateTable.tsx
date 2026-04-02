"use client";

import React, { useState, useMemo } from "react";
import { Rate } from "@/lib/api";
import clsx from "clsx";

interface RateTableProps {
  rates: Rate[];
  loading?: boolean;
}

type SortField = "rate_value" | "effective_date" | "provider_name" | "none";
type SortOrder = "asc" | "desc";

/**
 * Sortable rate comparison table.
 * Displays latest rates per provider, sortable by rate value and effective date.
 * Responsive design: stacks on mobile, table on desktop.
 */
export function RateComparisonTable({
  rates,
  loading = false,
}: RateTableProps) {
  const [sortField, setSortField] = useState<SortField>("rate_value");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  const sortedRates = useMemo(() => {
    if (!rates || rates.length === 0) return [];

    const sorted = [...rates].sort((a, b) => {
      let aVal: any = a;
      let bVal: any = b;

      if (sortField === "rate_value") {
        aVal = parseFloat(a.rate_value);
        bVal = parseFloat(b.rate_value);
      } else if (sortField === "effective_date") {
        aVal = new Date(a.effective_date).getTime();
        bVal = new Date(b.effective_date).getTime();
      } else if (sortField === "provider_name") {
        aVal = a.provider.name;
        bVal = b.provider.name;
      }

      if (aVal < bVal) return sortOrder === "asc" ? -1 : 1;
      if (aVal > bVal) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [rates, sortField, sortOrder]);

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field)
      return <span className="text-gray-400 ml-1">⇅</span>;
    return <span className="ml-1">{sortOrder === "asc" ? "▲" : "▼"}</span>;
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading rates...</span>
      </div>
    );
  }

  if (!rates || rates.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No rates available</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="overflow-x-auto">
        <table className="w-full text-sm md:text-base">
          <thead className="bg-gradient-to-r from-blue-50 to-blue-100 border-b-2 border-blue-300 sticky top-0">
            <tr>
              <th className="px-3 py-3 md:px-4 text-left font-semibold text-gray-700">
                <button
                  onClick={() => handleSort("provider_name")}
                  className="hover:text-blue-700 w-full text-left flex items-center gap-1"
                  title="Click to sort"
                >
                  🏦 Provider
                  <SortIcon field="provider_name" />
                </button>
              </th>
              <th className="px-3 py-3 md:px-4 text-left font-semibold text-gray-700">
                📈 Type
              </th>
              <th className="px-3 py-3 md:px-4 text-right font-semibold text-gray-700">
                <button
                  onClick={() => handleSort("rate_value")}
                  className="hover:text-blue-700 w-full text-right flex items-center justify-end gap-1"
                  title="Click to sort"
                >
                  Rate
                  <SortIcon field="rate_value" />
                </button>
              </th>
              <th className="px-3 py-3 md:px-4 text-left font-semibold text-gray-700">
                <button
                  onClick={() => handleSort("effective_date")}
                  className="hover:text-blue-700 w-full text-left flex items-center gap-1"
                  title="Click to sort"
                >
                  📅 Updated
                  <SortIcon field="effective_date" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sortedRates.map((rate, idx) => (
              <tr
                key={rate.id}
                className="hover:bg-blue-50 transition duration-150 even:bg-gray-50"
              >
                <td className="px-3 py-3 md:px-4 font-medium text-gray-900">
                  <span className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                    {rate.provider.name}
                  </span>
                </td>
                <td className="px-3 py-3 md:px-4 text-sm text-gray-600">
                  <span className="inline-block bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded">
                    {rate.rate_type.name}
                  </span>
                </td>
                <td className="px-3 py-3 md:px-4 text-right font-bold">
                  <span
                    className={clsx(
                      "text-lg py-1 px-2 rounded",
                      parseFloat(rate.rate_value) > 5
                        ? "bg-red-100 text-red-700"
                        : parseFloat(rate.rate_value) > 3
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-green-100 text-green-700",
                    )}
                  >
                    {parseFloat(rate.rate_value).toFixed(4)}%
                  </span>
                </td>
                <td className="px-3 py-3 md:px-4 text-sm text-gray-600">
                  {new Date(rate.effective_date).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sortedRates.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>📭 No rates available</p>
        </div>
      )}
    </div>
  );
}
