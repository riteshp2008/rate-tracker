/**
 * API client for Rate-Tracker backend.
 */
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface Rate {
  id: number;
  provider: { id: number; name: string };
  rate_type: { id: number; name: string };
  rate_value: string;
  effective_date: string;
  ingestion_timestamp: string;
  created_at: string;
}

export interface RateHistory {
  id: number;
  provider_name: string;
  rate_type_name: string;
  rate_value: string;
  effective_date: string;
  ingestion_timestamp: string;
}

export interface HistoryResponse {
  count: number;
  page: number;
  page_size: number;
  results: RateHistory[];
}

export interface Provider {
  id: number;
  name: string;
}

export interface RateType {
  id: number;
  name: string;
  description?: string;
}

class RatesAPI {
  /**
   * Fetch latest rates with optional type filter.
   */
  async getLatestRates(rateType?: string): Promise<Rate[]> {
    try {
      const params = rateType ? { type: rateType } : {};
      const response = await apiClient.get("/rates/latest/", { params });
      return response.data;
    } catch (error) {
      console.error("Error fetching latest rates:", error);
      throw error;
    }
  }

  /**
   * Fetch rate history for a provider + type with optional date filters.
   */
  async getRateHistory(
    provider: string,
    rateType: string,
    from?: string,
    to?: string,
    page?: number,
  ): Promise<HistoryResponse> {
    try {
      const params: any = { provider, type: rateType };
      if (from) params.from = from;
      if (to) params.to = to;
      if (page) params.page = page;

      const response = await apiClient.get("/rates/history/", { params });
      return response.data;
    } catch (error) {
      console.error("Error fetching rate history:", error);
      throw error;
    }
  }

  /**
   * Fetch list of all providers.
   */
  async getProviders(): Promise<Provider[]> {
    try {
      const response = await apiClient.get("/rates/providers/");
      return response.data;
    } catch (error) {
      console.error("Error fetching providers:", error);
      throw error;
    }
  }

  /**
   * Fetch list of all rate types.
   */
  async getRateTypes(): Promise<RateType[]> {
    try {
      const response = await apiClient.get("/rates/types/");
      return response.data;
    } catch (error) {
      console.error("Error fetching rate types:", error);
      throw error;
    }
  }
}

export default new RatesAPI();
