/**
 * @file lib/api/weather.ts
 * @brief Weather board, coordinate forecast and saved places. The server
 *        proxies the providers; temperatures arrive in Celsius.
 */
import { apiDelete, apiGet, apiPost, seg } from "./client";

export interface WeatherDay {
  date: string;
  code: number | null;
  max_c: number | null;
  min_c: number | null;
  precip: number | null;
}

export interface Forecast {
  current: { temp_c: number | null; code: number | null; is_day: boolean };
  daily: WeatherDay[];
}

export interface BoardItem {
  id: string;
  kind: "self" | "place" | "person";
  label: string;
  place: string | null;
  lat: number;
  lon: number;
  user_id: string | null;
  avatar_url: string | null;
  forecast: Forecast | null;
}

export interface WeatherPlace {
  id: string;
  name: string;
  lat: number;
  lon: number;
  created_at: string;
}

export const getWeatherBoard = () =>
  apiGet<BoardItem[]>("/api/v1/weather/board");
export const getForecast = (lat: number, lon: number) =>
  apiGet<Forecast | null>(
    `/api/v1/weather/forecast?${new URLSearchParams({ lat: String(lat), lon: String(lon) })}`,
  );
export const addWeatherPlace = (body: {
  name: string;
  lat: number;
  lon: number;
}) => apiPost<WeatherPlace>("/api/v1/weather/places", body);
export const removeWeatherPlace = (id: string) =>
  apiDelete<{ message: string }>(`/api/v1/weather/places/${seg(id)}`);
