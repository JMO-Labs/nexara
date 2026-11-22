"use client";
/**
 * @file components/events/EventMiniMap.tsx
 * @brief Read-only Leaflet mini-map for an event location.
 *
 * Tiles via Carto basemap CDN — no API key required.
 * Attribution: © OpenStreetMap contributors © CARTO.
 */
import * as React from "react";
import { useTheme } from "next-themes";
import { MapContainer, TileLayer, CircleMarker, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

interface EventMiniMapProps {
  lat: number;
  lon: number;
  height?: number | string;
  zoom?: number;
  ariaLabel?: string;
}

// CARTO basemaps now need an API key; OSM standard tiles don't. Dark mode
// inverts the light tiles (.nx-tiles-dark in globals.css).
const TILES = {
  url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  attribution:
    '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors',
};

/**
 * Force Leaflet to re-measure the container after mount + on parent resize.
 * Needed when the map lives inside an animated drawer / hidden tab.
 */
function InvalidateOnMount() {
  const map = useMap();
  React.useEffect(() => {
    const fix = () => map.invalidateSize();
    const t1 = setTimeout(fix, 0);
    const t2 = setTimeout(fix, 250);
    const t3 = setTimeout(fix, 600);
    const ro = new ResizeObserver(() => fix());
    const container = map.getContainer();
    ro.observe(container);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      ro.disconnect();
    };
  }, [map]);
  return null;
}

export function EventMiniMap({
  lat,
  lon,
  height = 200,
  zoom = 14,
  ariaLabel = "Event location map",
}: EventMiniMapProps) {
  const { resolvedTheme } = useTheme();
  const dark = resolvedTheme === "dark";

  return (
    <div
      role="img"
      aria-label={ariaLabel}
      style={{
        position: "relative",
        width: "100%",
        height,
        borderRadius: 8,
        overflow: "hidden",
        border: "1px solid color-mix(in srgb, var(--nx-ink) 15%, transparent)",
        backgroundColor: "var(--nx-bg)",
      }}
    >
      <MapContainer
        center={[lat, lon]}
        zoom={zoom}
        scrollWheelZoom={false}
        zoomControl={false}
        attributionControl
        style={{ width: "100%", height: "100%" }}
        key={dark ? "dark" : "light"}
      >
        <InvalidateOnMount />
        <TileLayer
          key={dark ? "dark" : "light"}
          url={TILES.url}
          attribution={TILES.attribution}
          className={dark ? "nx-tiles-dark" : undefined}
        />
        <CircleMarker
          center={[lat, lon]}
          radius={8}
          pathOptions={{
            color: "#fff",
            weight: 2,
            fillColor: "var(--nx-accent, #1f6feb)",
            fillOpacity: 1,
          }}
        />
      </MapContainer>
    </div>
  );
}

export default EventMiniMap;
