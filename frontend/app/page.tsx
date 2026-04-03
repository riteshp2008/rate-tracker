"use client";

import React, { useState, useEffect, useCallback } from "react";
import ratesAPI, { Rate, Provider, RateType } from "@/lib/api";
import { RateComparisonTable } from "@/components/RateTable";
import { RateHistoryChart } from "@/components/RateHistoryChart";
import { LoadingSpinner, ErrorMessage, SuccessMessage } from "@/components/ui";
import { format, subDays } from "date-fns";

/**
 * Main dashboard component.
 * - Displays rate comparison table (sortable & filterable)
 * - Shows 30-day history chart with statistics
 * - Auto-refreshes every 60 seconds
 * - Handles loading and error states
 * - Provider and type filtering
 */
export default function Dashboard() {
  const [rates, setRates] = useState<Rate[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [rateTypes, setRateTypes] = useState<RateType[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string>("");
  const [selectedType, setSelectedType] = useState<string>("");
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [mounted, setMounted] = useState(false);

  // Fetch latest rates
  const fetchLatestRates = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ratesAPI.getLatestRates();
      setRates(data);
      setLastRefresh(new Date());
      setSuccess("Rates updated successfully");
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to fetch rates. Is the API running?");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch providers and types
  const fetchMetadata = useCallback(async () => {
    try {
      const [providersList, typesList] = await Promise.all([
        ratesAPI.getProviders(),
        ratesAPI.getRateTypes(),
      ]);
      setProviders(providersList);
      setRateTypes(typesList);
      if (providersList.length > 0 && !selectedProvider) {
        setSelectedProvider(providersList[0].name);
      }
      if (typesList.length > 0 && !selectedType) {
        setSelectedType(typesList[0].name);
      }
    } catch (err: any) {
      console.error("Failed to fetch metadata:", err);
    }
  }, [selectedProvider, selectedType]);

  // Initial load
  useEffect(() => {
    setMounted(true);
    setLastRefresh(new Date());
    fetchMetadata();
    fetchLatestRates();
  }, []);

  // Auto-refresh every 60 seconds
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchLatestRates();
    }, 60000);

    return () => clearInterval(interval);
  }, [fetchLatestRates, autoRefresh]);

  // Filter rates based on provider, type, and search
  const filteredRates = rates.filter((rate) => {
    const providerMatch =
      !selectedProvider || rate.provider.name === selectedProvider;
    const typeMatch = !selectedType || rate.rate_type.name === selectedType;
    const searchMatch =
      !searchTerm ||
      rate.provider.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      rate.rate_type.name.toLowerCase().includes(searchTerm.toLowerCase());
    return providerMatch && typeMatch && searchMatch;
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600">
                💰 Rate Tracker
              </h1>
              <p className="text-xs text-gray-500 mt-1">
                Last updated:{" "}
                {lastRefresh
                  ? format(lastRefresh, "MMM dd, HH:mm:ss")
                  : "loading..."}
                {autoRefresh && " • Auto-refreshing enabled"}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition ${
                  autoRefresh
                    ? "bg-green-100 text-green-700 hover:bg-green-200"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
              >
                {autoRefresh ? "🔄 Auto-On" : "⏸ Auto-Off"}
              </button>
              <button
                onClick={fetchLatestRates}
                disabled={loading}
                className="px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:shadow-lg transition disabled:opacity-50"
              >
                {loading ? "⟳ Refreshing..." : "⟳ Refresh"}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && <ErrorMessage message={error} />}
        {success && <SuccessMessage message={success} />}

        {loading && rates.length === 0 ? (
          <LoadingSpinner />
        ) : (
          <>
            {/* Statistics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-white p-5 rounded-lg shadow-md hover:shadow-lg transition border-l-4 border-blue-600">
                <div className="text-gray-600 text-sm font-medium">
                  Providers
                </div>
                <div className="text-3xl font-bold text-blue-600 mt-1">
                  {providers.length}
                </div>
              </div>
              <div className="bg-white p-5 rounded-lg shadow-md hover:shadow-lg transition border-l-4 border-green-600">
                <div className="text-gray-600 text-sm font-medium">
                  Rate Types
                </div>
                <div className="text-3xl font-bold text-green-600 mt-1">
                  {rateTypes.length}
                </div>
              </div>
              <div className="bg-white p-5 rounded-lg shadow-md hover:shadow-lg transition border-l-4 border-orange-600">
                <div className="text-gray-600 text-sm font-medium">
                  Tracked Rates
                </div>
                <div className="text-3xl font-bold text-orange-600 mt-1">
                  {rates.length}
                </div>
              </div>
              <div className="bg-white p-5 rounded-lg shadow-md hover:shadow-lg transition border-l-4 border-purple-600">
                <div className="text-gray-600 text-sm font-medium">
                  Filtered
                </div>
                <div className="text-3xl font-bold text-purple-600 mt-1">
                  {filteredRates.length}
                </div>
              </div>
            </div>

            {/* Filter Section */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h3 className="text-lg font-bold mb-4 flex items-center">
                <span className="mr-2">🔍</span> Quick Filters
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Search */}
                <input
                  type="text"
                  placeholder="Search by provider or type..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {/* Provider Filter */}
                <select
                  value={selectedProvider}
                  onChange={(e) => setSelectedProvider(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  <option value="">All Providers</option>
                  {providers.map((p) => (
                    <option key={p.id} value={p.name}>
                      {p.name}
                    </option>
                  ))}
                </select>
                {/* Type Filter */}
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                >
                  <option value="">All Types</option>
                  {rateTypes.map((t) => (
                    <option key={t.id} value={t.name}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
              {(searchTerm || selectedProvider || selectedType) && (
                <button
                  onClick={() => {
                    setSearchTerm("");
                    setSelectedProvider("");
                    setSelectedType("");
                  }}
                  className="mt-3 px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition"
                >
                  Clear Filters
                </button>
              )}
            </div>

            {/* Rates Table */}
            {filteredRates.length > 0 ? (
              <div className="bg-white rounded-lg shadow-md p-6 mb-8">
                <h2 className="text-2xl font-bold mb-6 flex items-center">
                  <span className="mr-2">📊</span> Latest Rates
                </h2>
                <RateComparisonTable rates={filteredRates} loading={loading} />
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-md p-12 text-center text-gray-500 mb-8">
                <p className="text-lg">No rates match your filters</p>
                <p className="text-sm mt-2">
                  Try adjusting your search criteria
                </p>
              </div>
            )}
          </>
        )}

        {/* Footer */}
        <footer className="text-center text-xs text-gray-500 py-6 border-t border-gray-200 mt-8">
          <p>
            Rate Tracker •{" "}
            {autoRefresh
              ? "Auto-refreshing every 60s"
              : "Auto-refresh disabled"}{" "}
            •{" "}
            <a
              href="http://localhost:8000/api/"
              className="text-blue-600 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              API Docs
            </a>
          </p>
        </footer>
      </main>
    </div>
  );
}
