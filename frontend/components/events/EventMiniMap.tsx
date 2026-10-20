"use client";
/**
 * @file components/events/EventMiniMap.tsx
 * @brief Read-only Leaflet mini-map for an event location.
 *
 * Tiles via Carto basemap CDN — no API key required.
 * Attribution: © OpenStreetMap contributors © CARTO.
 */
import * as React from "react";
import { useColorScheme } from "@mui/joy/styles";
import { MapContainer, TileLayer, CircleMarker, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

interface EventMiniMapProps {
  lat: number;
  lon: number;
  height?: number | string;
  zoom?: number;
  ariaLabel?: string;
}

const TILES = {
  light: {
    url: "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
  dark: {
    url: "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
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
  const { mode, systemMode } = useColorScheme();
  const effective = mode === "system" ? systemMode : mode;
  const tiles = effective === "dark" ? TILES.dark : TILES.light;

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
        border: "1px solid var(--joy-palette-divider)",
        backgroundColor: "var(--joy-palette-background-level1)",
      }}
    >
      <MapContainer
        center={[lat, lon]}
        zoom={zoom}
        scrollWheelZoom={false}
        zoomControl={false}
        attributionControl
        style={{ width: "100%", height: "100%" }}
        key={effective}
      >
        <InvalidateOnMount />
        <TileLayer url={tiles.url} attribution={tiles.attribution} />
        <CircleMarker
          center={[lat, lon]}
          radius={8}
          pathOptions={{
            color: "#fff",
            weight: 2,
            fillColor: "var(--joy-palette-primary-solidBg, #1f6feb)",
            fillOpacity: 1,
          }}
        />
      </MapContainer>
    </div>
  );
}

export default EventMiniMap;
