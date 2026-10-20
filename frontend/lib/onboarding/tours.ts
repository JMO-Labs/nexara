/**
 * @file tours.ts
 * @brief Tour step definitions for onboarding guided tours.
 *
 * Defines separate tour flows for regular members and admins,
 * with step targets matching data-tour attributes in components.
 */

import type { Step } from "react-joyride";

/**
 * @brief Member onboarding tour with 5 core feature steps.
 *
 * Steps: TopBar search, Sidebar nav, Composer, Notifications bell, Settings.
 */
export const memberTour: Step[] = [
  {
    target: '[data-tour="topbar-search"]',
    content:
      "Use the search bar to find posts, members, events, and more across your community",
    title: "Search",
    placement: "bottom",
  },
  {
    target: '[data-tour="sidebar-nav"]',
    content:
      "Navigate between Feed, Events, Chat, Media, and Groups using the sidebar",
    title: "Navigation",
    placement: "right",
  },
  {
    target: '[data-tour="composer"]',
    content:
      "Write and share updates, photos, and links with your community here",
    title: "Share with Community",
    placement: "top",
  },
  {
    target: '[data-tour="bell"]',
    content:
      "Stay updated with notifications about new posts, comments, events, and messages",
    title: "Notifications",
    placement: "bottom",
  },
  {
    target: '[data-tour="settings"]',
    content:
      "Customize your profile, privacy settings, and notification preferences",
    title: "Settings",
    placement: "left",
  },
];

/**
 * @brief Admin onboarding tour with 4 admin-specific steps.
 *
 * Steps: Admin link, Invites tab, Users tab, SSO setup.
 */
export const adminTour: Step[] = [
  {
    target: '[data-tour="admin-link"]',
    content: "Access community administration and management tools",
    title: "Admin Panel",
    placement: "bottom",
  },
  {
    target: '[data-tour="admin-invites"]',
    content: "Send invites to add new members to your community",
    title: "Invitations",
    placement: "right",
  },
  {
    target: '[data-tour="admin-users"]',
    content: "View and manage community members and their roles",
    title: "Users",
    placement: "right",
  },
  {
    target: '[data-tour="admin-sso"]',
    content: "Configure single sign-on for seamless authentication",
    title: "SSO Setup",
    placement: "right",
  },
];
