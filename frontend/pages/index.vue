<!--
  @file pages/index.vue
  @brief Public landing page (pre-rendered).

  The first page visitors see. Displays the community name, tagline,
  feature highlights, self-hosted emphasis, and call-to-action buttons.
  Pre-rendered at build time for fast load and SEO.
-->
<template>
  <div>
    <NuxtLayout name="public">
      <!-- Hero Section -->
      <section
        class="flex min-h-[70vh] flex-col items-center justify-center px-4 text-center"
      >
        <h1
          class="mb-4 text-4xl font-extrabold tracking-tight text-gray-900 dark:text-white sm:text-5xl lg:text-6xl"
        >
          {{ $t("landing.hero.title", { communityName: $t("app.name") }) }}
        </h1>
        <p class="mb-8 max-w-2xl text-lg text-gray-600 dark:text-gray-300">
          {{ $t("landing.hero.subtitle") }}
        </p>
        <div class="flex flex-wrap items-center justify-center gap-4">
          <a
            href="/auth/register"
            class="rounded-lg bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {{ $t("landing.hero.getStarted") }}
          </a>
          <a
            href="https://github.com/com-nexara/nexara"
            target="_blank"
            rel="noopener noreferrer"
            class="rounded-lg border border-border px-6 py-3 text-sm font-semibold text-foreground hover:bg-accent"
          >
            {{ $t("landing.hero.viewOnGithub") }}
          </a>
        </div>
      </section>

      <!-- Features Section -->
      <section class="mx-auto max-w-6xl px-4 py-16">
        <h2
          class="mb-12 text-center text-3xl font-bold text-gray-900 dark:text-white"
        >
          {{ $t("landing.features.title") }}
        </h2>
        <div class="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <FeatureCard
            v-for="feature in features"
            :key="feature.titleKey"
            :icon="feature.icon"
            :title="$t(feature.titleKey)"
            :description="$t(feature.descKey)"
          />
        </div>
      </section>

      <!-- Self-hosted Section -->
      <section class="bg-gray-100 px-4 py-16 dark:bg-gray-800">
        <div class="mx-auto max-w-3xl text-center">
          <h2 class="mb-4 text-3xl font-bold text-gray-900 dark:text-white">
            {{ $t("landing.selfHosted.title") }}
          </h2>
          <p class="text-lg text-gray-600 dark:text-gray-300">
            {{ $t("landing.selfHosted.description") }}
          </p>
        </div>
      </section>

      <!-- Install Section -->
      <section class="mx-auto max-w-4xl px-4 py-16">
        <h2
          class="mb-4 text-center text-3xl font-bold text-gray-900 dark:text-white"
        >
          {{ $t("landing.install.title") }}
        </h2>
        <p class="mb-8 text-center text-gray-600 dark:text-gray-300">
          {{ $t("landing.install.description") }}
        </p>
        <div class="rounded-lg bg-gray-900 p-6 text-sm">
          <code class="text-green-400">docker compose up -d</code>
        </div>
      </section>

      <!-- Footer -->
      <footer
        class="border-t border-gray-200 px-4 py-8 text-center text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400"
      >
        <p>{{ $t("app.name") }} &mdash; {{ $t("app.tagline") }}</p>
      </footer>
    </NuxtLayout>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Landing page setup with feature list data.
 */

definePageMeta({ layout: false });

/** @brief Feature cards displayed in the features section. */
const features = [
  {
    icon: "📰",
    titleKey: "landing.features.feed",
    descKey: "landing.features.feedDesc",
  },
  {
    icon: "📅",
    titleKey: "landing.features.events",
    descKey: "landing.features.eventsDesc",
  },
  {
    icon: "💬",
    titleKey: "landing.features.chat",
    descKey: "landing.features.chatDesc",
  },
  {
    icon: "🖼️",
    titleKey: "landing.features.media",
    descKey: "landing.features.mediaDesc",
  },
  {
    icon: "📱",
    titleKey: "landing.features.pwa",
    descKey: "landing.features.pwaDesc",
  },
];

/**
 * @brief Inline FeatureCard component for the landing page.
 */
const FeatureCard = {
  props: { icon: String, title: String, description: String },
  template: `
    <div class="rounded-lg border border-gray-200 bg-white p-6 text-center dark:border-gray-700 dark:bg-gray-800">
      <span class="mb-3 block text-3xl">{{ icon }}</span>
      <h3 class="mb-2 text-lg font-semibold text-gray-900 dark:text-white">{{ title }}</h3>
      <p class="text-sm text-gray-600 dark:text-gray-300">{{ description }}</p>
    </div>
  `,
};
</script>
