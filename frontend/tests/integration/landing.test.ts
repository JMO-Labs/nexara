/**
 * @file tests/integration/landing.test.ts
 * @brief Integration test for the landing page rendering.
 *
 * Verifies the landing page mounts correctly with i18n keys rendered,
 * features section present, and call-to-action links functional.
 */

import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import LandingPage from "~/pages/index.vue";

describe("landing page integration", () => {
  const createWrapper = () =>
    mount(LandingPage, {
      global: {
        mocks: {
          $t: (key: string, params?: Record<string, string>) => {
            const translations: Record<string, string> = {
              "landing.hero.title": `Welcome to ${params?.communityName || "Nexara"}`,
              "landing.hero.subtitle": "A private space for your community.",
              "landing.hero.getStarted": "Get Started",
              "landing.hero.viewOnGithub": "View on GitHub",
              "landing.features.title": "Everything your community needs",
              "landing.features.feed": "Activity Feed",
              "landing.features.feedDesc": "Share updates.",
              "landing.features.events": "Events",
              "landing.features.eventsDesc": "Plan gatherings.",
              "landing.features.chat": "Chat",
              "landing.features.chatDesc": "Stay connected.",
              "landing.features.media": "Photos",
              "landing.features.mediaDesc": "Share memories.",
              "landing.features.pwa": "Works Offline",
              "landing.features.pwaDesc": "Install as an app.",
              "landing.selfHosted.title": "Self-hosted & Private",
              "landing.selfHosted.description":
                "Your data stays on your server.",
              "landing.install.title": "Get Started in Minutes",
              "landing.install.description": "One command.",
              "app.name": "Nexara",
              "app.tagline": "Your community platform",
            };
            return translations[key] || key;
          },
        },
        stubs: {
          NuxtLayout: { template: "<div><slot /></div>" },
          NuxtPage: { template: "<div />" },
        },
      },
    });

  it("renders the hero section with community name", () => {
    const wrapper = createWrapper();

    expect(wrapper.text()).toContain("Welcome to Nexara");
  });

  it("renders the features section", () => {
    const wrapper = createWrapper();

    expect(wrapper.text()).toContain("Everything your community needs");
    expect(wrapper.text()).toContain("Activity Feed");
    expect(wrapper.text()).toContain("Events");
    expect(wrapper.text()).toContain("Chat");
  });

  it("renders the self-hosted section", () => {
    const wrapper = createWrapper();

    expect(wrapper.text()).toContain("Self-hosted & Private");
    expect(wrapper.text()).toContain("Your data stays on your server.");
  });

  it("has a get started link to registration", () => {
    const wrapper = createWrapper();
    const link = wrapper.find('a[href="/auth/register"]');

    expect(link.exists()).toBe(true);
    expect(link.text()).toContain("Get Started");
  });

  it("has the docker compose command in install section", () => {
    const wrapper = createWrapper();

    expect(wrapper.text()).toContain("docker compose up -d");
  });

  it("renders footer with app name", () => {
    const wrapper = createWrapper();

    expect(wrapper.find("footer").exists()).toBe(true);
    expect(wrapper.text()).toContain("Nexara");
  });
});
