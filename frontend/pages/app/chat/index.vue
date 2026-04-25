<!--
  @file pages/app/chat/index.vue
  @brief Chat landing page with channel sidebar + empty state.

  Presents the list of channels on the left; selecting one navigates
  to /app/chat/{channelId}. Acts as the empty-state default when no
  channel is selected yet.
-->
<template>
  <div
    class="flex h-[calc(100vh-8rem)] overflow-hidden rounded-lg border border-border bg-background"
  >
    <div class="w-64 shrink-0">
      <ChannelSidebar
        :channels="chatStore.channels"
        :unread-by-channel="chatStore.unreadByChannel"
        :active-channel-id="null"
        @select="onSelect"
      />
    </div>
    <div
      class="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground"
      data-testid="chat-empty-placeholder"
    >
      {{ $t("chat.selectChannel") }}
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Chat index page.
 */
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useChatStore } from "~/stores/chat";
import ChannelSidebar from "~/components/chat/ChannelSidebar.vue";
import type { ChatChannel } from "~/types/api";

definePageMeta({ middleware: "auth" });

const chatStore = useChatStore();
const router = useRouter();

onMounted(async () => {
  await chatStore.fetchChannels();
});

function onSelect(channel: ChatChannel): void {
  router.push(`/app/chat/${channel.id}`);
}
</script>
