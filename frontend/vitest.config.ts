/**
 * @file vitest.config.ts
 * @brief Vitest test runner configuration for the Nexara frontend.
 *
 * Uses happy-dom for DOM simulation. Path aliases match Nuxt's `~/` convention.
 * Coverage is collected from source directories only (excludes tests and config).
 */

import { defineConfig } from "vitest/config";
import { resolve } from "path";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],

  resolve: {
    alias: {
      "~": resolve(__dirname, "."),
      "@": resolve(__dirname, "."),
      "#app": resolve(__dirname, "./tests/__mocks__/nuxt-app.ts"),
      "#imports": resolve(__dirname, "./tests/__mocks__/nuxt-imports.ts"),
    },
  },

  test: {
    globals: true,
    environment: "happy-dom",
    include: ["tests/**/*.test.ts"],
    setupFiles: ["./tests/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "cobertura"],
      include: [
        "stores/**",
        "composables/**",
        "components/**",
        "middleware/**",
        "utils/**",
      ],
    },
  },
});
