/**
 * @file nuxt.config.ts
 * @brief Nuxt 3 application configuration.
 *
 * Configures hybrid rendering (pre-rendered landing, SPA for authenticated app),
 * Tailwind CSS, Pinia, i18n, VueUse, PWA, and runtime API settings.
 */

export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',

  devtools: { enabled: true },

  /** @brief Hybrid rendering: static landing page, SPA for authenticated routes. */
  routeRules: {
    '/': { prerender: true },
    '/about': { prerender: true },
    '/app/**': { ssr: false },
  },

  /** @brief Nuxt modules in load order. */
  modules: [
    '@nuxt/eslint',
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt',
    '@nuxtjs/i18n',
    '@vueuse/nuxt',
    '@vite-pwa/nuxt',
  ],

  /** @brief Global CSS entry point (Tailwind directives + custom properties). */
  css: ['~/assets/css/main.css'],

  /** @brief Tailwind module configuration. */
  tailwindcss: {
    configPath: '~/tailwind.config.ts',
  },

  /** @brief i18n configuration — en-US only for Phase 1. */
  i18n: {
    locales: [{ code: 'en-US', file: 'en-US.json' }],
    defaultLocale: 'en-US',
    lazy: true,
    langDir: 'locales',
    strategy: 'no_prefix',
  },

  /** @brief PWA manifest and service worker configuration. */
  pwa: {
    registerType: 'autoUpdate',
    manifest: {
      name: 'Nexara',
      short_name: 'Nexara',
      description: 'Self-hosted community platform',
      theme_color: '#3b82f6',
      background_color: '#ffffff',
      display: 'standalone',
      icons: [
        { src: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
        { src: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png' },
        {
          src: '/icons/icon-512x512-maskable.png',
          sizes: '512x512',
          type: 'image/png',
          purpose: 'maskable',
        },
      ],
    },
    workbox: {
      navigateFallback: '/app',
      runtimeCaching: [
        {
          urlPattern: /^https?:\/\/.*\/api\/.*/i,
          handler: 'NetworkFirst',
          options: { cacheName: 'api-cache', expiration: { maxEntries: 100, maxAgeSeconds: 300 } },
        },
      ],
    },
  },

  /** @brief Runtime configuration exposed to the client. */
  runtimeConfig: {
    public: {
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || '/api/v1',
    },
  },

  /** @brief TypeScript strict mode. */
  typescript: {
    strict: true,
  },

  /**
   * @brief Nitro server configuration.
   *
   * In development, proxies /api and /ws requests to the FastAPI backend
   * so the frontend can use relative URLs that work identically in dev
   * and production (where Nginx handles the proxy).
   */
  nitro: {
    devProxy: {
      '/api': { target: 'http://localhost:8000/api', changeOrigin: true },
      '/ws': { target: 'http://localhost:8000/ws', changeOrigin: true, ws: true },
      '/.well-known': { target: 'http://localhost:8000/.well-known', changeOrigin: true },
      '/healthz': { target: 'http://localhost:8000/healthz', changeOrigin: true },
    },
  },
})
