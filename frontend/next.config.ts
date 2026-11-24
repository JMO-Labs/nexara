/**
 * @file next.config.ts
 * @brief Next 16 (Turbopack) config. Pin workspace root to silence
 *        multi-lockfile inference; transpile MUI Joy/Material for SSR.
 *        `/api/*` rewrites to the FastAPI backend so the browser sees a
 *        same-origin call — sidesteps CORS in development. The HttpOnly
 *        refresh cookie remains path-scoped to /api/v1/auth, so the
 *        nx_session hint cookie still gates /app/** at the edge.
 */
import type { NextConfig } from "next";
import path from "node:path";
import { execSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

const API_TARGET = process.env.NEXARA_API_TARGET ?? "http://localhost:8000";

/** @brief Write public/sw-version.js (git sha, else timestamp) for the SW. */
function writeSwVersion(): string {
  let v = String(Date.now());
  try {
    v =
      execSync("git rev-parse --short HEAD", {
        stdio: ["ignore", "pipe", "ignore"],
      })
        .toString()
        .trim() || v;
  } catch {
    /* no git (docker build): timestamp */
  }
  try {
    writeFileSync(
      path.resolve(__dirname, "public/sw-version.js"),
      `self.__SW_VERSION__ = ${JSON.stringify(v)};\n`,
    );
  } catch {
    /* read-only fs: SW falls back to "dev" */
  }
  return v;
}
const BUILD_ID = writeSwVersion();

const nextConfig: NextConfig = {
  reactStrictMode: true,
  env: { NEXT_PUBLIC_BUILD_ID: BUILD_ID },
  // Standalone output bundles a self-contained `.next/standalone/server.js`
  // for the production Docker image — no `node_modules` ship needed.
  output: "standalone",
  turbopack: {
    root: path.resolve(__dirname),
  },
  transpilePackages: ["@mui/joy", "@mui/material", "@mui/system", "@mui/utils"],
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API_TARGET}/api/:path*` },
      { source: "/ws/:path*", destination: `${API_TARGET}/ws/:path*` },
    ];
  },
};

export default withNextIntl(nextConfig);
