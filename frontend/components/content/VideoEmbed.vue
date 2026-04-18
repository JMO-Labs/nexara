<!--
  @file components/content/VideoEmbed.vue
  @brief Click-to-play video embed for YouTube, Vimeo, Twitch, Dailymotion, PeerTube.

  Initially shows thumbnail with play button overlay.
  On click, replaces with iframe for the provider.
-->
<template>
  <div
    class="relative aspect-video overflow-hidden rounded-lg border border-border bg-muted"
    data-testid="video-embed"
  >
    <!-- Thumbnail + play button (before click) -->
    <div
      v-if="!playing"
      class="flex h-full w-full cursor-pointer items-center justify-center"
      @click="playing = true"
    >
      <img
        v-if="thumbnailUrl"
        :src="thumbnailUrl"
        alt=""
        class="absolute inset-0 h-full w-full object-cover"
      >
      <div
        class="absolute inset-0 flex items-center justify-center bg-black/30"
      >
        <button
          type="button"
          class="flex h-16 w-16 items-center justify-center rounded-full bg-primary/90 text-primary-foreground transition-transform hover:scale-110"
          data-testid="play-button"
          :aria-label="'Play video'"
        >
          <svg
            class="ml-1 h-8 w-8"
            fill="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M8 5v14l11-7z" />
          </svg>
        </button>
      </div>
    </div>

    <!-- iframe (after click) -->
    <iframe
      v-else
      :src="embedUrl"
      class="h-full w-full"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen
    />
  </div>
</template>

<script setup lang="ts">
/**
 * @brief VideoEmbed — click-to-play video for supported providers.
 */
import { ref, computed } from "vue";

const props = defineProps<{
  /** @brief Provider type: youtube, vimeo, twitch, dailymotion, peertube. */
  providerType: string;
  /** @brief Provider-specific video ID. */
  providerId: string;
  /** @brief Optional thumbnail URL. */
  thumbnailUrl?: string;
}>();

const playing = ref(false);

/** @brief Build embed URL for the provider. */
const embedUrl = computed(() => {
  const type = props.providerType.toLowerCase();
  const id = props.providerId;

  switch (type) {
    case "youtube":
      return `https://www.youtube.com/embed/${id}`;
    case "vimeo":
      return `https://player.vimeo.com/video/${id}`;
    case "twitch":
      return `https://player.twitch.tv/?video=${id}`;
    case "dailymotion":
      return `https://www.dailymotion.com/embed/video/${id}`;
    case "peertube":
      return id.startsWith("http") ? id : `https://peertube.example.com/videos/embed/${id}`;
    default:
      return "";
  }
});
</script>
