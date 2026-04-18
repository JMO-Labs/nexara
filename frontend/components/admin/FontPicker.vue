<!--
  @file components/admin/FontPicker.vue
  @brief Font family dropdown with preview.
-->
<template>
  <div class="space-y-1">
    <label class="block text-sm font-medium text-foreground">
      {{ label }}
    </label>
    <select
      :value="modelValue"
      class="w-full rounded-lg border border-input bg-background px-3 py-2 text-foreground focus:ring-2 focus:ring-ring"
      data-testid="font-select"
      @change="onChange"
    >
      <option
        v-for="f in allowedFonts"
        :key="f"
        :value="f"
      >
        {{ f }}
      </option>
    </select>
    <p
      :style="{ fontFamily: modelValue }"
      data-testid="font-preview"
      class="text-sm text-muted-foreground"
    >
      {{ $t("admin.fontPreview") }}
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief FontPicker with allowed fonts and preview.
 */
const SANS_FONTS = [
  "Inter",
  "Roboto",
  "Open Sans",
  "Lato",
  "Poppins",
  "Montserrat",
  "Source Sans 3",
  "Noto Sans",
  "Raleway",
  "Ubuntu",
  "system-ui",
];

const MONO_FONTS = [
  "JetBrains Mono",
  "Fira Code",
  "Source Code Pro",
  "IBM Plex Mono",
  "system-ui",
];

const props = withDefaults(
  defineProps<{
  /** @brief Selected font family. */
  modelValue: string;
  /** @brief Label for the select. */
  label: string;
  /** @brief Font variant: sans or mono. */
  variant?: "sans" | "mono";
}>(),
  { variant: "sans" },
);

const allowedFonts = props.variant === "mono" ? MONO_FONTS : SANS_FONTS;

const emit = defineEmits<{
  (e: "update:modelValue", font: string): void;
}>();

function onChange(e: Event): void {
  const target = e.target as HTMLSelectElement;
  emit("update:modelValue", target.value);
}
</script>
