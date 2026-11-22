/**
 * @file tests/unit/weather/weather.test.tsx
 * @brief Weather helpers and WeatherTile rows/unit toggle.
 */
import { describe, it, expect, vi } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import { renderWithProviders } from "../../utils/renderWithProviders";
import { defaultUnit, describe as wx, temp } from "@/lib/weather";

const board = [
  {
    id: "me",
    kind: "self",
    label: "Leo",
    place: "Mesa, Arizona",
    lat: 33.4,
    lon: -111.8,
    user_id: "me",
    avatar_url: null,
    forecast: {
      current: { temp_c: 20, code: 0, is_day: true },
      daily: [
        { date: "2026-11-21", code: 0, max_c: 25, min_c: 10, precip: 0 },
        { date: "2026-11-22", code: 61, max_c: 18, min_c: 9, precip: 80 },
      ],
    },
  },
  {
    id: "p1",
    kind: "place",
    label: "Cabin",
    place: null,
    lat: 44,
    lon: -73,
    user_id: null,
    avatar_url: null,
    forecast: null,
  },
];
const remove = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/app",
}));
vi.mock("@/hooks/useWeather", async (orig) => ({
  ...(await orig<typeof import("@/hooks/useWeather")>()),
  useWeatherBoard: () => ({ data: board, isLoading: false }),
  useWeatherPlaces: () => ({
    add: { mutate: vi.fn(), error: null },
    remove: { mutate: remove },
  }),
}));

import { WeatherTile } from "@/components/home/tiles/WeatherTile";

describe("weather helpers", () => {
  it("converts and formats temperatures", () => {
    expect(temp(20, "C")).toBe("20°");
    expect(temp(20, "F")).toBe("68°");
    expect(temp(null, "F")).toBe("–");
  });
  it("maps WMO codes and day/night", () => {
    expect(wx(61).label).toBe("Rain");
    expect(wx(0, false).label).toBe("Clear");
    expect(wx(95).label).toBe("Thunderstorms");
  });
  it("defaults to °F only for US-style locales", () => {
    expect(defaultUnit("en-US")).toBe("F");
    expect(defaultUnit("en-GB")).toBe("C");
    expect(defaultUnit("es-MX")).toBe("C");
  });
});

describe("WeatherTile", () => {
  it("shows you first, unavailable places, and switches units", () => {
    localStorage.setItem("nx-temp-unit", "C");
    renderWithProviders(<WeatherTile open onToggle={vi.fn()} />);
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("Mesa, Arizona")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("20°").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "°F" }));
    expect(screen.getAllByText("68°").length).toBeGreaterThan(0);
    expect(localStorage.getItem("nx-temp-unit")).toBe("F");
  });
});
