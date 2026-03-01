<!--
  @file pages/app/settings/notifications.vue
  @brief Notification preferences tab.

  Matrix table: rows = types (mention, comment, reaction, new_post,
  system, invite_accepted), cols = channels (In-app, Email).
  Checkboxes bound to notification preference fields. Save button
  calls settingsStore.updateNotificationPreferences().
-->
<template>
  <div class="flex-1 rounded-lg border border-border bg-card p-6">
    <div class="overflow-x-auto">
      <table class="w-full min-w-[400px] text-left text-sm">
        <thead>
          <tr class="border-b border-border">
            <th class="pb-3 pr-4 font-medium text-foreground">
              {{ $t("settings.notifications") }}
            </th>
            <th class="px-4 pb-3 font-medium text-foreground">
              {{ $t("settings.inApp") }}
            </th>
            <th class="px-4 pb-3 font-medium text-foreground">
              {{ $t("settings.emailChannel") }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in notificationRows"
            :key="row.type"
            class="border-b border-border last:border-0"
          >
            <td class="py-3 pr-4 text-foreground">
              {{ $t(row.label) }}
            </td>
            <td class="px-4 py-3">
              <input
                :id="`${row.type}_inapp`"
                v-model="prefs[row.inappKey]"
                type="checkbox"
                class="h-4 w-4 rounded border-input text-primary focus:ring-ring"
              />
            </td>
            <td class="px-4 py-3">
              <input
                :id="`${row.type}_email`"
                v-model="prefs[row.emailKey]"
                type="checkbox"
                :disabled="prefs.mute_all_email"
                class="h-4 w-4 rounded border-input text-primary focus:ring-ring disabled:opacity-50"
              />
            </td>
          </tr>
          <tr class="border-b border-border last:border-0">
            <td class="py-3 pr-4 text-foreground">
              {{ $t("settings.muteAllEmail") }}
            </td>
            <td class="px-4 py-3" />
            <td class="px-4 py-3">
              <input
                id="mute_all_email"
                v-model="prefs.mute_all_email"
                type="checkbox"
                class="h-4 w-4 rounded border-input text-primary focus:ring-ring"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <button
      class="mt-6 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
      :disabled="settingsStore.loading"
      @click="handleSave"
    >
      {{ settingsStore.loading ? $t("common.loading") : $t("common.save") }}
    </button>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief Notification preferences matrix with save action.
 */
import { reactive, onMounted, watch } from "vue";
import { useSettingsStore } from "~/stores/settings";
import { useUiStore } from "~/stores/ui";

const settingsStore = useSettingsStore();
const uiStore = useUiStore();
const { t: $t } = useI18n();

const notificationRows = [
  {
    type: "mention",
    label: "settings.mention",
    inappKey: "notif_mention_inapp",
    emailKey: "notif_mention_email",
  },
  {
    type: "comment",
    label: "settings.comment",
    inappKey: "notif_comment_inapp",
    emailKey: "notif_comment_email",
  },
  {
    type: "reaction",
    label: "settings.reaction",
    inappKey: "notif_reaction_inapp",
    emailKey: "notif_reaction_email",
  },
  {
    type: "new_post",
    label: "settings.newPost",
    inappKey: "notif_new_post_inapp",
    emailKey: "notif_new_post_email",
  },
  {
    type: "system",
    label: "settings.system",
    inappKey: "notif_system_inapp",
    emailKey: "notif_system_email",
  },
  {
    type: "invite_accepted",
    label: "settings.inviteAccepted",
    inappKey: "notif_invite_accepted_inapp",
    emailKey: "notif_invite_accepted_email",
  },
];

const prefs = reactive<Record<string, boolean>>({
  notif_mention_inapp: false,
  notif_mention_email: false,
  notif_comment_inapp: false,
  notif_comment_email: false,
  notif_reaction_inapp: false,
  notif_reaction_email: false,
  notif_new_post_inapp: false,
  notif_new_post_email: false,
  notif_system_inapp: false,
  notif_system_email: false,
  notif_invite_accepted_inapp: false,
  notif_invite_accepted_email: false,
  mute_all_email: false,
});

onMounted(async () => {
  await settingsStore.fetchSettings();
  syncFromStore();
});

watch(() => settingsStore.settings, syncFromStore, { deep: true });

function syncFromStore(): void {
  const s = settingsStore.settings;
  if (!s) return;
  prefs.notif_mention_inapp = s.notif_mention_inapp;
  prefs.notif_mention_email = s.notif_mention_email;
  prefs.notif_comment_inapp = s.notif_comment_inapp;
  prefs.notif_comment_email = s.notif_comment_email;
  prefs.notif_reaction_inapp = s.notif_reaction_inapp;
  prefs.notif_reaction_email = s.notif_reaction_email;
  prefs.notif_new_post_inapp = s.notif_new_post_inapp;
  prefs.notif_new_post_email = s.notif_new_post_email;
  prefs.notif_system_inapp = s.notif_system_inapp;
  prefs.notif_system_email = s.notif_system_email;
  prefs.notif_invite_accepted_inapp = s.notif_invite_accepted_inapp;
  prefs.notif_invite_accepted_email = s.notif_invite_accepted_email;
  prefs.mute_all_email = s.mute_all_email;
}

async function handleSave(): Promise<void> {
  try {
    await settingsStore.updateNotificationPreferences({
      notif_mention_inapp: prefs.notif_mention_inapp,
      notif_mention_email: prefs.notif_mention_email,
      notif_comment_inapp: prefs.notif_comment_inapp,
      notif_comment_email: prefs.notif_comment_email,
      notif_reaction_inapp: prefs.notif_reaction_inapp,
      notif_reaction_email: prefs.notif_reaction_email,
      notif_new_post_inapp: prefs.notif_new_post_inapp,
      notif_new_post_email: prefs.notif_new_post_email,
      notif_system_inapp: prefs.notif_system_inapp,
      notif_system_email: prefs.notif_system_email,
      notif_invite_accepted_inapp: prefs.notif_invite_accepted_inapp,
      notif_invite_accepted_email: prefs.notif_invite_accepted_email,
      mute_all_email: prefs.mute_all_email,
    });
    uiStore.showToast({
      type: "success",
      message: $t("settings.notificationsSaved"),
    });
  } catch (error) {
    uiStore.showToast({
      type: "error",
      message: error instanceof Error ? error.message : $t("common.error"),
    });
  }
}
</script>
