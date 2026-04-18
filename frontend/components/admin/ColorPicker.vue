<!--
  @file components/admin/ColorPicker.vue
  @brief Color picker with clickable swatch, native picker popover, and hex input.

  Click the swatch to open the native color picker. Type a hex code directly.
  Optional contrast ratio display against a reference color.
-->
<template>
  <div class="space-y-1.5">
    <label class="block text-sm font-medium text-foreground">
      {{ label }}
    </label>
    <div class="flex items-center gap-2">
      <!-- Clickable swatch that triggers hidden native color input -->
      <button
        type="button"
        class="relative h-10 w-10 shrink-0 cursor-pointer rounded-lg border-2 border-border shadow-sm transition-shadow hover:shadow-md focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        :style="{ backgroundColor: colorValue }"
        :aria-label="`${label}: ${colorValue}`"
        data-testid="color-swatch"
        @click="openPicker"
      >
        <input
          ref="nativeInput"
          v-model="colorValue"
          type="color"
          class="absolute inset-0 cursor-pointer opacity-0"
          tabindex="-1"
          data-testid="color-input"
          @input="onColorInput"
        />
      </button>
      <!-- Hex text input -->
      <input
        v-model="hexValue"
        type="text"
        class="w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-sm text-foreground focus:ring-2 focus:ring-ring"
        placeholder="#000000"
        maxlength="7"
        data-testid="hex-input"
        @change="onHexChange"
      />
    </div>
    <div
      v-if="contrastAgainst"
      data-testid="contrast-ratio"
      class="flex items-center gap-2 text-xs"
    >
      <span class="text-muted-foreground">
        {{ $t("admin.contrastRatio") }}: {{ contrastDisplay }}
      </span>
      <span
        :class="passesAa ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'"
      >
        {{ passesAa ? $t("admin.wcagAA") : $t("admin.wcagFail") }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief ColorPicker with clickable swatch, native picker, and hex input.
 */
import { ref, watch, computed } from "vue";
import { contrastRatio } from "~/utils/contrast";

const props = withDefaults(
  defineProps<{
    /** @brief Current color value (hex). */
    modelValue: string;
    /** @brief Label for the input. */
    label: string;
    /** @brief Optional background color for contrast check. */
    contrastAgainst?: string;
  }>(),
  { contrastAgainst: undefined },
);

const emit = defineEmits<{
  (e: "update:modelValue", color: string): void;
}>();

const nativeInput = ref<HTMLInputElement | null>(null);
const colorValue = ref(props.modelValue);
const hexValue = ref(props.modelValue);

watch(
  () => props.modelValue,
  (v) => {
    colorValue.value = v;
    hexValue.value = v;
  },
);

const contrastDisplay = computed(() => {
  if (!props.contrastAgainst) return "";
  const ratio = contrastRatio(props.modelValue, props.contrastAgainst);
  return ratio.toFixed(2);
});

const passesAa = computed(() => {
  if (!props.contrastAgainst) return true;
  const ratio = contrastRatio(props.modelValue, props.contrastAgainst);
  return ratio >= 4.5;
});

function normalizeHex(val: string): string {
  const m = val.match(/^#?([0-9a-fA-F]{6})$/);
  if (m) return `#${m[1].toLowerCase()}`;
  return props.modelValue;
}

function openPicker(): void {
  nativeInput.value?.click();
}

function onColorInput(): void {
  const hex = colorValue.value;
  hexValue.value = hex;
  emit("update:modelValue", hex);
}

function onHexChange(): void {
  const hex = normalizeHex(hexValue.value);
  colorValue.value = hex;
  hexValue.value = hex;
  emit("update:modelValue", hex);
}
</script>
