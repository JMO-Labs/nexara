/**
 * @file plugins/i18n.ts
 * @brief Nuxt i18n plugin configuration.
 *
 * Sets the default locale to en-US. Additional locale configuration
 * is handled in nuxt.config.ts via the @nuxtjs/i18n module. This
 * plugin provides a hook point for runtime locale switching and
 * any additional i18n setup needed beyond module defaults.
 */

export default defineNuxtPlugin((_nuxtApp) => {
  /* Module-level i18n configuration is in nuxt.config.ts.
   * This plugin is a hook point for future runtime locale switching
   * or locale-dependent initialization (e.g., date-fns locale). */
})
