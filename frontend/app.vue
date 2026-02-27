<!--
  @file app.vue
  @brief Root application component.

  Wraps all pages in NuxtLayout for layout switching between
  public (landing/auth) and default (authenticated app) layouts.
-->
<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
