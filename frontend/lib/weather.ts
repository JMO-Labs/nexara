/**
 * @file lib/weather.ts
 * @brief WMO weather codes -> label + icon, and °C/°F display.
 */
import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudMoon,
  CloudRain,
  CloudSnow,
  CloudSun,
  Moon,
  Sun,
  type LucideIcon,
} from "lucide-react";

export type TempUnit = "C" | "F";

/**
 * @brief Label and icon for a WMO code.
 * @param code WMO weather interpretation code
 * @param day daytime (sun vs moon icons)
 */
export function describe(
  code: number | null,
  day = true,
): { label: string; Icon: LucideIcon } {
  const c = code ?? -1;
  if (c === 0) return { label: "Clear", Icon: day ? Sun : Moon };
  if (c <= 2)
    return { label: "Partly cloudy", Icon: day ? CloudSun : CloudMoon };
  if (c === 3) return { label: "Cloudy", Icon: Cloud };
  if (c === 45 || c === 48) return { label: "Fog", Icon: CloudFog };
  if (c >= 51 && c <= 57) return { label: "Drizzle", Icon: CloudDrizzle };
  if ((c >= 61 && c <= 67) || (c >= 80 && c <= 82))
    return { label: "Rain", Icon: CloudRain };
  if ((c >= 71 && c <= 77) || c === 85 || c === 86)
    return { label: "Snow", Icon: CloudSnow };
  if (c >= 95) return { label: "Thunderstorms", Icon: CloudLightning };
  return { label: "Unknown", Icon: Cloud };
}

/** @brief Fahrenheit for US-style locales, else Celsius. */
export function defaultUnit(
  locale = globalThis.navigator?.language ?? "en-US",
): TempUnit {
  return /^en-(US|LR|MM)$|^(my|en-PW)/.test(locale) ? "F" : "C";
}

/** @brief "72°" in the chosen unit, or "–" when missing. */
export function temp(c: number | null | undefined, unit: TempUnit): string {
  if (c == null) return "–";
  return `${Math.round(unit === "F" ? (c * 9) / 5 + 32 : c)}°`;
}
