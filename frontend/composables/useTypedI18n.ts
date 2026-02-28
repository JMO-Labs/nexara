/**
 * @file composables/useTypedI18n.ts
 * @brief Type-safe wrapper around vue-i18n's useI18n composable.
 *
 * Provides compile-time validation of translation keys so that
 * missing or mistyped keys are caught by TypeScript rather than
 * silently rendering raw key strings at runtime.
 *
 * @example
 * ```ts
 * const { t } = useTypedI18n();
 * t("settings.displayName");          // OK
 * t("settings.nonExistent");          // TS error
 * t("feed.showAllComments", { count: 5 }); // OK with params
 * ```
 */

import type { TranslationKey } from "~/types/i18n-keys";

/** @brief Named interpolation values for translation strings. */
type TranslationParams = Record<string, string | number>;

/**
 * @brief Return type from useTypedI18n — mirrors useI18n but with typed keys.
 */
interface TypedI18n {
  /** @brief Translate a key with optional named parameters. */
  t: (key: TranslationKey, params?: TranslationParams) => string;
}

/**
 * @brief Type-safe i18n composable wrapping @nuxtjs/i18n's useI18n.
 *
 * Constrains the key parameter to the `TranslationKey` union type
 * generated from the locale JSON, preventing raw-key display bugs.
 *
 * @returns Object with a typed `t` function.
 */
export function useTypedI18n(): TypedI18n {
  const { t: rawT } = useI18n();

  function t(key: TranslationKey, params?: TranslationParams): string {
    return params ? rawT(key, params) : rawT(key);
  }

  return { t };
}
