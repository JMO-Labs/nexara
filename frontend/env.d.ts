/**
 * @file env.d.ts
 * @brief Ambient type declarations and references for the frontend.
 *
 * The root tsconfig.json excludes `.nuxt/` to avoid type-checking
 * generated build artefacts.  The reference directive below brings in
 * only the auto-import declarations (defineNuxtRouteMiddleware,
 * navigateTo, useRoute, etc.) so the IDE resolves them correctly.
 *
 * The wildcard module declaration lets TypeScript resolve `*.vue`
 * single-file component imports without per-file type stubs.
 */

/// <reference path="./.nuxt/types/imports.d.ts" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, unknown>;
  export default component;
}
