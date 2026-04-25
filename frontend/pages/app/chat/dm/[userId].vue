<!--
  @file pages/app/chat/dm/[userId].vue
  @brief Direct-message thread view — resolves or creates a DM channel.

  On mount, POSTs /chat/dm/{peerId} to ensure the channel exists,
  then redirects to /app/chat/{channelId}. Displays a lightweight
  loading state while the resolution is in flight.
-->
<template>
  <div
    class="flex h-[calc(100vh-8rem)] items-center justify-center rounded-lg border border-border bg-background"
  >
    <p class="text-sm text-muted-foreground" data-testid="chat-dm-loading">
      <span v-if="error">{{ error }}</span>
      <span v-else>{{ $t("chat.loading") }}</span>
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief DM thread resolver page.
 */
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useChatStore } from "~/stores/chat";

definePageMeta({ middleware: "auth" });

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const error = ref<string | null>(null);

onMounted(async () => {
  const peerId = String(route.params.userId ?? "");
  if (!peerId) {
    error.value = "Missing user id";
    return;
  }
  try {
    const channel = await chatStore.openDm(peerId);
    await router.replace(`/app/chat/${channel.id}`);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to open DM";
  }
});
</script>
