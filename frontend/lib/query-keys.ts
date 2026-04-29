/**
 * @file lib/query-keys.ts
 * @brief Centralized TanStack Query keys. Hierarchical per backend router.
 *        Use these everywhere — never hand-roll keys at call sites.
 */

export const qk = {
  auth: {
    me: () => ["auth", "me"] as const,
    session: () => ["auth", "session"] as const,
  },
  feed: {
    all: () => ["feed"] as const,
    list: (filters?: Record<string, unknown>) =>
      ["feed", "list", filters ?? {}] as const,
    infinite: (filters?: Record<string, unknown>) =>
      ["feed", "infinite", filters ?? {}] as const,
    post: (id: string) => ["feed", "post", id] as const,
    comments: (postId: string) => ["feed", "post", postId, "comments"] as const,
    promptPost: (id: string) => ["feed", "prompt-post", id] as const,
    promptResponses: (promptPostId: string) =>
      ["feed", "prompt-responses", promptPostId] as const,
  },
  posts: {
    all: () => ["posts"] as const,
    list: (filters?: Record<string, unknown>) =>
      ["posts", "list", filters ?? {}] as const,
  },
  chat: {
    channels: () => ["chat", "channels"] as const,
    messages: (channelId: string) => ["chat", "messages", channelId] as const,
    dms: () => ["chat", "dms"] as const,
    subgroupChannel: (subgroupId: string) => ["chat", "subgroup-channel", subgroupId] as const,
  },
  subgroups: {
    all: () => ["subgroups"] as const,
    list: () => ["subgroups", "list"] as const,
    detail: (slug: string) => ["subgroups", "detail", slug] as const,
    members: (slug: string) => ["subgroups", "members", slug] as const,
  },
  events: {
    all: () => ["events"] as const,
    list: (range?: { from?: string; to?: string; subgroup_id?: string }) =>
      ["events", "list", range ?? {}] as const,
    detail: (id: string) => ["events", "detail", id] as const,
    subscriptions: {
      all: () => ["events", "subscriptions"] as const,
      list: () => ["events", "subscriptions", "list"] as const,
      detail: (id: string) =>
        ["events", "subscriptions", "detail", id] as const,
    },
  },
  calendars: {
    all: () => ["calendars"] as const,
    list: () => ["calendars", "list"] as const,
  },
  galleries: {
    all: () => ["galleries"] as const,
    list: (filters?: Record<string, unknown>) =>
      ["galleries", "list", filters ?? {}] as const,
    detail: (id: string) => ["galleries", "detail", id] as const,
  },
  media: {
    list: (filters?: Record<string, unknown>) =>
      ["media", "list", filters ?? {}] as const,
  },
  notifications: {
    list: () => ["notifications", "list"] as const,
    unread: () => ["notifications", "unread"] as const,
  },
  search: {
    global: (q: string, scope?: string) =>
      ["search", q, scope ?? "all"] as const,
  },
  admin: {
    users: (filters?: Record<string, unknown>) =>
      ["admin", "users", filters ?? {}] as const,
    branding: () => ["admin", "branding"] as const,
    invites: () => ["admin", "invites"] as const,
    auditLog: () => ["admin", "audit-log"] as const,
    metrics: () => ["admin", "metrics"] as const,
    settings: () => ["admin", "settings"] as const,
    oauth: () => ["admin", "oauth"] as const,
    interestsAnalytics: () => ["admin", "interests-analytics"] as const,
    prompts: () => ["admin", "prompts"] as const,
  },
  settings: {
    profile: () => ["settings", "profile"] as const,
    notifications: () => ["settings", "notifications"] as const,
    security: () => ["settings", "security"] as const,
  },
  home: {
    layout: () => ["home-layout"] as const,
    summary: () => ["home-summary"] as const,
    media: (limit?: number) => ["home-media", limit ?? 24] as const,
  },
} as const;
