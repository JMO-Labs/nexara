<!--
  @file pages/app/admin/branding.vue
  @brief Full branding editor page (admin only).

  Loads current branding from GET /branding/, sections for Colors, Fonts,
  Email, Landing, PWA. Submit via PUT /branding/ with toast on success.
  Wide layout with 3-column color grid and side preview.
-->
<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-foreground">
      {{ $t("admin.branding") }}
    </h1>

    <div
      v-if="authStore.user?.role !== 'admin'"
      class="rounded-lg border border-border bg-card p-6 text-center text-muted-foreground"
    >
      {{ $t("common.loading") }}
    </div>

    <template v-else>
      <div class="grid gap-6 xl:grid-cols-3">
        <!-- Left: editing forms (spans 2 cols on xl) -->
        <div class="space-y-6 xl:col-span-2">
          <!-- Community identity -->
          <div class="rounded-lg border border-border bg-card p-6">
            <h2 class="mb-4 text-lg font-semibold text-foreground">
              {{ $t("admin.displayName") }}
            </h2>
            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  for="community-name"
                  class="mb-1 block text-sm font-medium text-foreground"
                >
                  {{ $t("admin.displayName") }}
                </label>
                <input
                  id="community-name"
                  v-model="form.community_name"
                  type="text"
                  class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <label
                  for="cta-text"
                  class="mb-1 block text-sm font-medium text-foreground"
                >
                  CTA Text
                </label>
                <input
                  id="cta-text"
                  v-model="form.landing_cta_text"
                  type="text"
                  class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>
          </div>

          <!-- Colors -->
          <div class="rounded-lg border border-border bg-card p-6">
            <h2 class="mb-4 text-lg font-semibold text-foreground">
              {{ $t("admin.colors") }}
            </h2>
            <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <AdminColorPicker
                v-model="form.color_primary"
                :label="$t('admin.colorPrimary')"
              />
              <AdminColorPicker
                v-model="form.color_primary_dark"
                :label="$t('admin.colorPrimaryDark')"
              />
              <AdminColorPicker
                v-model="form.color_accent"
                :label="$t('admin.colorAccent')"
              />
              <AdminColorPicker
                v-model="form.color_surface_light"
                :label="$t('admin.colorSurfaceLight')"
              />
              <AdminColorPicker
                v-model="form.color_surface_dark"
                :label="$t('admin.colorSurfaceDark')"
              />
              <AdminColorPicker
                v-model="form.color_text_light"
                :label="$t('admin.colorTextLight')"
                :contrast-against="form.color_surface_light"
              />
              <AdminColorPicker
                v-model="form.color_text_dark"
                :label="$t('admin.colorTextDark')"
                :contrast-against="form.color_surface_dark"
              />
            </div>
          </div>

          <!-- Fonts -->
          <div class="rounded-lg border border-border bg-card p-6">
            <h2 class="mb-4 text-lg font-semibold text-foreground">
              {{ $t("admin.fonts") }}
            </h2>
            <div class="grid gap-4 sm:grid-cols-2">
              <AdminFontPicker
                v-model="form.font_family"
                :label="$t('admin.fontFamily')"
              />
              <AdminFontPicker
                v-model="form.font_family_mono"
                :label="$t('admin.fontFamilyMono')"
                variant="mono"
              />
            </div>
          </div>

          <!-- Contrast warnings -->
          <div
            v-if="contrastWarnings.length > 0"
            class="rounded-lg border border-yellow-300 bg-yellow-50 p-4 dark:border-yellow-700 dark:bg-yellow-950/30"
          >
            <h3 class="mb-2 font-medium text-foreground">
              {{ $t("admin.contrastWarnings") }}
            </h3>
            <ul class="list-inside list-disc text-sm text-muted-foreground">
              <li
                v-for="(w, i) in contrastWarnings"
                :key="i"
              >
                {{ w.color1 }} / {{ w.color2 }}: {{ w.ratio }}:1
                {{ w.passes_aa ? $t("admin.wcagAA") : $t("admin.wcagFail") }}
              </li>
            </ul>
          </div>

          <button
            data-testid="branding-submit"
            :disabled="loading"
            class="rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            @click="handleSubmit"
          >
            {{ loading ? $t("common.loading") : $t("common.save") }}
          </button>
        </div>

        <!-- Right: Preview (sticky) -->
        <div class="xl:sticky xl:top-6 xl:self-start">
          <div class="rounded-lg border border-border bg-card p-6">
            <h2 class="mb-4 text-lg font-semibold text-foreground">
              {{ $t("admin.preview") }}
            </h2>
            <AdminBrandingPreview :branding="form" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Admin branding editor with colors, fonts, and live preview.
 */
import { ref, reactive, onMounted, watch } from "vue";
import { useAuthStore } from "~/stores/auth";
import { useApi } from "~/composables/useApi";
import { useUiStore } from "~/stores/ui";
import { useBranding } from "~/composables/useBranding";
import type {
  BrandingResponse,
  BrandingUpdateResponse,
  BrandingFormData,
  ContrastWarning,
} from "~/types/api";

const authStore = useAuthStore();
const api = useApi();
const uiStore = useUiStore();
const { fetchBranding } = useBranding();

const loading = ref(false);
const contrastWarnings = ref<ContrastWarning[]>([]);

const form = reactive<BrandingFormData>({
  community_name: "Nexara",
  tagline: null,
  color_primary: "#3b82f6",
  color_primary_dark: "#2563eb",
  color_accent: "#8b5cf6",
  color_surface_light: "#ffffff",
  color_surface_dark: "#1f2937",
  color_text_light: "#111827",
  color_text_dark: "#f9fafb",
  font_family: "Inter",
  font_family_mono: "JetBrains Mono",
  landing_cta_text: "Join our community",
});

async function loadBranding(): Promise<void> {
  try {
    const data = await api.get<BrandingResponse>("/branding/");
    Object.assign(form, {
      community_name: data.community_name,
      tagline: data.tagline ?? null,
      color_primary: data.color_primary,
      color_primary_dark: data.color_primary_dark,
      color_accent: data.color_accent ?? "#8b5cf6",
      color_surface_light: data.color_surface_light ?? "#ffffff",
      color_surface_dark: data.color_surface_dark ?? "#1f2937",
      color_text_light: data.color_text_light ?? "#111827",
      color_text_dark: data.color_text_dark ?? "#f9fafb",
      font_family: data.font_family ?? "Inter",
      font_family_mono: data.font_family_mono ?? "JetBrains Mono",
      landing_cta_text: data.landing_cta_text ?? "Join our community",
    });
  } catch {
    /* use defaults */
  }
}

async function handleSubmit(): Promise<void> {
  loading.value = true;
  contrastWarnings.value = [];
  try {
    const res = await api.put<BrandingUpdateResponse>("/branding/", {
      community_name: form.community_name,
      tagline: form.tagline,
      color_primary: form.color_primary,
      color_primary_dark: form.color_primary_dark,
      color_accent: form.color_accent,
      color_surface_light: form.color_surface_light,
      color_surface_dark: form.color_surface_dark,
      color_text_light: form.color_text_light,
      color_text_dark: form.color_text_dark,
      font_family: form.font_family,
      font_family_mono: form.font_family_mono,
      landing_cta_text: form.landing_cta_text,
    });
    contrastWarnings.value = res?.contrast_warnings ?? [];
    await fetchBranding();
    uiStore.showToast({
      type: "success",
      message: "Branding saved",
    });
  } catch (e) {
    uiStore.showToast({
      type: "error",
      message: e instanceof Error ? e.message : "Failed to save",
    });
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  if (authStore.user?.role === "admin") {
    await loadBranding();
  }
});

watch(
  () => authStore.user?.role,
  (role) => {
    if (role === "admin") loadBranding();
  },
);
</script>
