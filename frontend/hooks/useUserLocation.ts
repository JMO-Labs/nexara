'use client';
/**
 * @file hooks/useUserLocation.ts
 * @brief Best-effort user latitude/longitude for biasing autocompletes.
 *
 * Order of attempts:
 *   1. Cached value in sessionStorage (skip network).
 *   2. ``navigator.geolocation`` (requires explicit user permission).
 *   3. IP geolocation via ipwho.is (free, no key, no signup).
 *
 * Resolves to ``null`` when all sources fail or the user denies.
 */
import * as React from 'react';

export interface UserLocation {
  lat: number;
  lon: number;
  source: 'browser' | 'ip';
}

const CACHE_KEY = 'nx.userLocation.v1';
const GEO_TIMEOUT_MS = 4_000;

function readCache(): UserLocation | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as UserLocation;
  } catch {
    return null;
  }
}

function writeCache(loc: UserLocation): void {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(loc));
  } catch {
    /* quota / unavailable — non-fatal */
  }
}

function tryBrowserGeo(): Promise<UserLocation | null> {
  return new Promise((resolve) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      resolve(null);
      return;
    }
    let settled = false;
    const finish = (v: UserLocation | null) => {
      if (settled) return;
      settled = true;
      resolve(v);
    };
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        finish({ lat: pos.coords.latitude, lon: pos.coords.longitude, source: 'browser' }),
      () => finish(null),
      { timeout: GEO_TIMEOUT_MS, maximumAge: 5 * 60_000, enableHighAccuracy: false },
    );
    setTimeout(() => finish(null), GEO_TIMEOUT_MS + 250);
  });
}

async function tryIpGeo(signal: AbortSignal): Promise<UserLocation | null> {
  try {
    const res = await fetch('https://ipwho.is/', { signal });
    if (!res.ok) return null;
    const data = (await res.json()) as {
      success?: boolean;
      latitude?: number;
      longitude?: number;
    };
    if (!data.success || data.latitude == null || data.longitude == null) return null;
    return { lat: data.latitude, lon: data.longitude, source: 'ip' };
  } catch {
    return null;
  }
}

export function useUserLocation(): UserLocation | null {
  const [loc, setLoc] = React.useState<UserLocation | null>(() => readCache());

  React.useEffect(() => {
    if (loc) return;
    let cancelled = false;
    const ctrl = new AbortController();
    (async () => {
      const browser = await tryBrowserGeo();
      if (cancelled) return;
      if (browser) {
        writeCache(browser);
        setLoc(browser);
        return;
      }
      const ip = await tryIpGeo(ctrl.signal);
      if (cancelled) return;
      if (ip) {
        writeCache(ip);
        setLoc(ip);
      }
    })();
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [loc]);

  return loc;
}
