/**
 * @file tests/__mocks__/nuxt-imports.ts
 * @brief Mock for Nuxt #imports auto-imports used in tests.
 *
 * Re-exports Vue composition API functions and Nuxt utilities so that
 * code using `import { ref } from '#imports'` resolves correctly in Vitest.
 */

export {
  ref,
  computed,
  reactive,
  watch,
  watchEffect,
  onMounted,
  onUnmounted,
  nextTick,
  toRef,
  toRefs,
  unref,
  isRef,
  shallowRef,
} from 'vue'

export { navigateTo, useRuntimeConfig, useRoute, useRouter } from './nuxt-app'
export { useI18n } from 'vue-i18n'
