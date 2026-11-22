"use client";
/**
 * @file hooks/useWeather.ts
 * @brief Weather board, saved-place mutations, forecast and °C/°F choice.
 */
import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addWeatherPlace,
  getForecast,
  getWeatherBoard,
  removeWeatherPlace,
} from "@/lib/api/weather";
import { defaultUnit, type TempUnit } from "@/lib/weather";

const KEY = ["weather"] as const;

/** @brief Board: your city, saved places, pinned people. */
export const useWeatherBoard = (enabled = true) =>
  useQuery({
    queryKey: [...KEY, "board"],
    queryFn: getWeatherBoard,
    staleTime: 15 * 60_000,
    enabled,
  });

/** @brief Forecast for coordinates (skipped when missing). */
export const useForecast = (lat?: number | null, lon?: number | null) =>
  useQuery({
    queryKey: [...KEY, "fc", lat, lon],
    queryFn: () => getForecast(lat!, lon!),
    enabled: lat != null && lon != null,
    staleTime: 30 * 60_000,
  });

/** @brief Add/remove a saved place; refreshes the board. */
export function useWeatherPlaces() {
  const qc = useQueryClient();
  const done = () => void qc.invalidateQueries({ queryKey: KEY });
  return {
    add: useMutation({ mutationFn: addWeatherPlace, onSuccess: done }),
    remove: useMutation({ mutationFn: removeWeatherPlace, onSuccess: done }),
  };
}

const UNIT_KEY = "nx-temp-unit";

/** @brief Temperature unit, remembered per browser. */
export function useTempUnit(): [TempUnit, (u: TempUnit) => void] {
  const [unit, setUnit] = React.useState<TempUnit>(() => {
    try {
      const v = localStorage.getItem(UNIT_KEY);
      if (v === "C" || v === "F") return v;
    } catch {
      /* storage blocked */
    }
    return defaultUnit();
  });
  const set = (u: TempUnit) => {
    setUnit(u);
    try {
      localStorage.setItem(UNIT_KEY, u);
    } catch {
      /* storage blocked */
    }
  };
  return [unit, set];
}
