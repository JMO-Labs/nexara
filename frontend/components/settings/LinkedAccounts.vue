<!--
  @file components/settings/LinkedAccounts.vue
  @brief Shows OAuth providers linked to the user's account.

  Placeholder component for future /api/v1/users/me/oauth-links integration.
  Ready to be wired into the user settings page when the API is available.
-->
<template>
  <div class="rounded-lg border border-border bg-card p-6">
    <h3 class="mb-2 text-lg font-semibold text-foreground">
      {{ $t("settings.linkedAccounts") }}
    </h3>
    <p class="mb-4 text-sm text-muted-foreground">
      {{ $t("settings.linkedAccountsDescription") }}
    </p>
    <div
      class="rounded-lg border border-dashed border-border bg-muted/30 p-6 text-center text-sm text-muted-foreground"
    >
      {{ $t("settings.linkedAccountsPlaceholder") }}
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * @brief LinkedAccounts — OAuth provider links for the current user.
 *
 * Will display linked providers from GET /api/v1/users/me/oauth-links
 * and support unlinking when the API is implemented.
 */
</script>
