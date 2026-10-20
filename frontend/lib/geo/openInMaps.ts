/**
 * @file lib/geo/openInMaps.ts
 * @brief Build a universal "Open in Maps" URL from a free-text location.
 *
 * Uses Google's `maps.google.com` URL scheme — opens the native Maps app
 * on iOS/Android (Google Maps if installed, otherwise Apple/system Maps),
 * and the web Google Maps on desktop. No API key required.
 */

export function mapsUrl(query: string): string {
  const q = encodeURIComponent(query.trim());
  return `https://www.google.com/maps/search/?api=1&query=${q}`;
}

export function mapsUrlForCoords(lat: number, lon: number): string {
  return `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;
}
