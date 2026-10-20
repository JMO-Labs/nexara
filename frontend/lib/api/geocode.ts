/**
 * @file lib/api/geocode.ts
 * @brief Photon (Komoot) geocoding wrapper. No API key required.
 *
 * @see https://photon.komoot.io/
 *
 * Photon ToS asks for a User-Agent and attribution. Browsers can't set
 * UA, but we keep request volume low via caller-side debouncing.
 */

const PHOTON_BASE = "https://photon.komoot.io/api";

export interface GeocodeBias {
  lat: number;
  lon: number;
}

export interface GeocodeResult {
  /** Display label, e.g. "123 Main St, Springfield, USA". */
  label: string;
  lat: number;
  lon: number;
  /** Stable hint for dedup / keys. */
  osm_id?: string;
  type?: string;
}

interface PhotonFeature {
  geometry: { coordinates: [number, number] };
  properties: {
    name?: string;
    street?: string;
    housenumber?: string;
    postcode?: string;
    city?: string;
    state?: string;
    country?: string;
    osm_id?: number;
    osm_type?: string;
    type?: string;
  };
}

function buildLabel(p: PhotonFeature["properties"]): string {
  const line1 = [p.housenumber, p.street].filter(Boolean).join(" ").trim();
  const head = p.name && p.name !== line1 ? p.name : line1;
  const tail = [p.city, p.state, p.country].filter(Boolean).join(", ");
  return [head, tail].filter(Boolean).join(", ");
}

export async function geocodeSearch(
  query: string,
  opts: { bias?: GeocodeBias; limit?: number; signal?: AbortSignal } = {},
): Promise<GeocodeResult[]> {
  const q = query.trim();
  if (q.length < 2) return [];
  const params = new URLSearchParams({
    q,
    limit: String(opts.limit ?? 6),
    lang: "en",
  });
  if (opts.bias) {
    params.set("lat", String(opts.bias.lat));
    params.set("lon", String(opts.bias.lon));
  }
  const res = await fetch(`${PHOTON_BASE}/?${params}`, { signal: opts.signal });
  if (!res.ok) return [];
  const data = (await res.json()) as { features?: PhotonFeature[] };
  const seen = new Set<string>();
  const out: GeocodeResult[] = [];
  for (const f of data.features ?? []) {
    const [lon, lat] = f.geometry.coordinates;
    const p = f.properties;
    const baseLabel =
      buildLabel(p) || p.name || `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
    const dedupKey =
      p.osm_type && p.osm_id
        ? `${p.osm_type}/${p.osm_id}`
        : `${baseLabel}@${lat.toFixed(5)},${lon.toFixed(5)}`;
    if (seen.has(dedupKey)) continue;
    seen.add(dedupKey);
    out.push({
      label: baseLabel,
      lat,
      lon,
      osm_id: dedupKey,
      type: p.type,
    });
  }
  return out;
}
