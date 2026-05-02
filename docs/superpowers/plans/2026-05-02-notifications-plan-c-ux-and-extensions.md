# Notifications Refactor — Plan C: UX + Plugin Polish

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Frontend rebuild on top of Plan A + B. Bell becomes active-only with prune-on-click/ack; new full-featured Drawer for history + filters + bulk actions; Toast↔Bell bridge auto-toasts based on `type.toast_on_arrival`; Settings rebuilt as a registry-driven matrix with DnD editor, snooze, digest cadence, and webhook list. Includes plugin-author docs.

**Architecture:** A frontend mirror of the backend registry (hydrated once via `GET /notifications/types`) drives every notification UI. Renderers and inline actions are looked up by `type.key`. The Bell + Drawer share data via react-query keys and stay in sync across tabs through SSE invalidation.

**Tech Stack:** Next.js (App Router) — see `frontend/AGENTS.md`: read `node_modules/next/dist/docs/` before any router/server-component decisions. Joy UI, framer-motion, zustand, @tanstack/react-query, next-intl, vitest + React Testing Library + happy-dom, Playwright.

**Spec:** `docs/superpowers/specs/2026-05-02-notifications-refactor-design.md` (sections 9, 12.4 smoke).

**Prerequisites:** Plan A and Plan B complete and merged.

---

## File Structure

| Path | Status | Purpose |
|---|---|---|
| `frontend/lib/notifications/types.ts` | Create | TS types mirroring `NotificationType` JSON schema |
| `frontend/lib/notifications/registry.ts` | Create | `useNotificationRegistry()` react-query hook |
| `frontend/lib/notifications/renderers.ts` | Create | `renderNotif(type, payload, t)` + per-type render registry |
| `frontend/lib/api/notifications.ts` | Modify | New endpoints (`/types`, `/active`, `/dismiss`, `/preferences`, `/snooze`, `/webhooks`) |
| `frontend/lib/api/webhooks.ts` | Create | Per-user + admin webhook calls |
| `frontend/stores/notifications.ts` | Create | Zustand: `drawerOpen`, `bulkSelection`, `optimisticDismiss` |
| `frontend/stores/toasts.ts` | Modify | Add `action?`, `priority`, `dedupeKey` |
| `frontend/components/ui/Toast.tsx` | Modify | Render action button; assertive variant for `danger` |
| `frontend/components/notifications/NotificationsBell.tsx` | Rewrite | Active-only; prune-on-click + ack |
| `frontend/components/notifications/NotificationsDrawer.tsx` | Create | Right slide-out, filters, bulk |
| `frontend/components/notifications/NotifRow.tsx` | Create | Registry-driven row + actions |
| `frontend/components/notifications/ToastBridge.tsx` | Create | SSE → toasts |
| `frontend/components/settings/NotificationsTab.tsx` | Rewrite | Auto-built matrix + DnD/snooze + cadence + webhooks |
| `frontend/components/settings/DnDScheduleEditor.tsx` | Create | Weekly grid + tz picker |
| `frontend/components/settings/SnoozeControls.tsx` | Create | Quick-snooze buttons + clear |
| `frontend/components/settings/WebhookList.tsx` | Create | List + actions |
| `frontend/components/settings/WebhookEditModal.tsx` | Create | Create/edit; secret reveal once |
| `frontend/app/app/layout.tsx` (or wherever ToastRoot is mounted) | Modify | Mount `<ToastBridge />` |
| `frontend/messages/en.json` | Modify | i18n keys for all new strings |
| `frontend/tests/unit/lib/notifications/renderers.test.ts` | Create | Per-type render |
| `frontend/tests/unit/components/notifications/NotificationsBell.test.tsx` | Modify | New active-only behavior |
| `frontend/tests/unit/components/notifications/NotificationsDrawer.test.tsx` | Create | Filters/bulk |
| `frontend/tests/unit/components/notifications/NotifRow.test.tsx` | Create | Action button → API call |
| `frontend/tests/unit/components/notifications/ToastBridge.test.tsx` | Create | SSE → toast |
| `frontend/tests/unit/components/settings/NotificationsTab.test.tsx` | Modify | Auto-built matrix |
| `frontend/tests/unit/components/settings/DnDScheduleEditor.test.tsx` | Create | Window add/remove + tz |
| `frontend/tests/unit/components/settings/WebhookList.test.tsx` | Create | CRUD UX |
| `frontend/tests/e2e/notifications.spec.ts` | Create | Bell badge → click → nav → bell prunes; multi-tab |
| `docs/plugins/notifications.md` | Create | Plugin-author guide |

---

## Task 1: API client extensions + TS types

**Files:**
- Create: `frontend/lib/notifications/types.ts`
- Modify: `frontend/lib/api/notifications.ts`
- Create: `frontend/lib/api/webhooks.ts`

- [ ] **Step 1: Author TS types**

`frontend/lib/notifications/types.ts`:

```ts
/**
 * @file lib/notifications/types.ts
 * @brief Frontend mirror of backend NotificationType registry JSON.
 */
export type Channel = 'inapp' | 'email' | 'push' | 'webhook' | 'toast';

export type Category =
  | 'social' | 'event' | 'gallery' | 'prompt' | 'system' | 'plugin';

export interface ActionDescriptor {
  key: string;
  label_i18n: string;
  method: 'POST' | 'PUT' | 'DELETE';
  url_template: string;
  style: 'primary' | 'neutral' | 'danger';
}

export interface NotificationTypeDescriptor {
  key: string;
  category: Category;
  default_channels: Record<Channel, boolean>;
  user_configurable: Channel[];
  group_window_seconds: number | null;
  toast_on_arrival: boolean;
  bypass_dnd: boolean;
  digestable: boolean;
  actions: ActionDescriptor[];
  label_i18n: string;
  icon: string;
  plugin_id: string | null;
  payload_schema: Record<string, unknown>;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  type: string;
  payload: Record<string, unknown>;
  read_at: string | null;
  dismissed_at: string | null;
  created_at: string;
  updated_at?: string;
  count?: number;
  actor_ids?: string[];
}

export interface PreferencesPayload {
  notification_prefs: Record<string, Partial<Record<Channel, boolean>>>;
  dnd_schedule: Record<string, { start: string; end: string }[]> | null;
  dnd_until: string | null;
  dnd_timezone: string;
  digest_cadence: Record<string, 'instant' | 'hourly' | 'daily' | 'off'>;
}
```

- [ ] **Step 2: Extend API client**

Append to `frontend/lib/api/notifications.ts`:

```ts
import type {
  NotificationItem, NotificationTypeDescriptor, PreferencesPayload,
} from '@/lib/notifications/types';

export const listTypes = () =>
  apiGet<NotificationTypeDescriptor[]>('/api/v1/notifications/types');

export const listActive = () =>
  apiGet<{ items: NotificationItem[] }>('/api/v1/notifications/active');

export const dismissOne = (id: string) =>
  apiPost<{ message: string }>(`/api/v1/notifications/${id}/dismiss`);

export const dismissAll = () =>
  apiPost<{ message: string }>('/api/v1/notifications/dismiss-all');

export const callAction = (id: string, key: string) =>
  apiPost<{ message: string }>(`/api/v1/notifications/${id}/actions/${key}`);

export const getPreferences = () =>
  apiGet<PreferencesPayload>('/api/v1/notifications/preferences');

export const patchPreferences = (body: Partial<PreferencesPayload>) =>
  apiPatch<PreferencesPayload>('/api/v1/notifications/preferences', body);

export const snooze = (duration: '1h' | 'until_morning' | string) =>
  apiPost<{ message: string }>('/api/v1/notifications/snooze', { duration });

export const clearSnooze = () =>
  apiDelete<{ message: string }>('/api/v1/notifications/snooze');
```

If `apiPatch` is missing, add it to `frontend/lib/api/client.ts` mirroring `apiPost` with `method: 'PATCH'`.

- [ ] **Step 3: Webhook client**

`frontend/lib/api/webhooks.ts`:

```ts
/**
 * @file lib/api/webhooks.ts
 * @brief Per-user + admin webhook subscription endpoints.
 */
import { apiGet, apiPost, apiPatch, apiDelete } from './client';

export interface WebhookListItem {
  id: string;
  url: string;
  type_keys: string[];
  enabled: boolean;
  failure_count: number;
  last_failure_at: string | null;
  created_at: string;
}

export interface WebhookCreateResponse extends WebhookListItem {
  secret: string;          // returned once on create
}

export const listWebhooks = () =>
  apiGet<WebhookListItem[]>('/api/v1/notifications/webhooks');

export const createWebhook = (body: { url: string; type_keys: string[] }) =>
  apiPost<WebhookCreateResponse>('/api/v1/notifications/webhooks', body);

export const updateWebhook = (id: string, body: Partial<Omit<WebhookListItem, 'id'>>) =>
  apiPatch<WebhookListItem>(`/api/v1/notifications/webhooks/${id}`, body);

export const deleteWebhook = (id: string) =>
  apiDelete<{ message: string }>(`/api/v1/notifications/webhooks/${id}`);

export const listCommunityWebhooks = (communityId: string) =>
  apiGet<WebhookListItem[]>(`/api/v1/communities/${communityId}/webhooks`);

export const createCommunityWebhook = (
  communityId: string, body: { url: string; type_keys: string[] },
) => apiPost<WebhookCreateResponse>(`/api/v1/communities/${communityId}/webhooks`, body);
```

- [ ] **Step 4: Lint + typecheck**

```bash
cd frontend && npx eslint lib/notifications lib/api && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/notifications/ frontend/lib/api/notifications.ts frontend/lib/api/webhooks.ts frontend/lib/api/client.ts
git commit -m "feat(notifications): TS types + API client for v2 endpoints"
```

---

## Task 2: Frontend registry hook + renderers

**Files:**
- Create: `frontend/lib/notifications/registry.ts`
- Create: `frontend/lib/notifications/renderers.ts`
- Test: `frontend/tests/unit/lib/notifications/renderers.test.ts`

- [ ] **Step 1: Failing test**

`frontend/tests/unit/lib/notifications/renderers.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { renderNotif } from '@/lib/notifications/renderers';
import type { NotificationTypeDescriptor } from '@/lib/notifications/types';

const t = (k: string): string => k;

const mention: NotificationTypeDescriptor = {
  key: 'mention', category: 'social',
  default_channels: { inapp: true, email: true, push: true, webhook: false, toast: true },
  user_configurable: ['inapp', 'email', 'push', 'toast'],
  group_window_seconds: null, toast_on_arrival: true,
  bypass_dnd: false, digestable: true,
  actions: [],
  label_i18n: 'notif.mention.label', icon: 'at-symbol', plugin_id: null,
  payload_schema: {},
};

describe('renderNotif', () => {
  it('returns title+body+icon for known type', () => {
    const r = renderNotif(mention, { message: 'hi', link: '/p/1' }, t);
    expect(r.title).toBe('notif.mention.label');
    expect(r.body).toBe('hi');
    expect(r.link).toBe('/p/1');
    expect(r.icon).toBe('at-symbol');
  });

  it('falls back to message-only when payload missing link', () => {
    const r = renderNotif(mention, { message: 'hi' }, t);
    expect(r.link).toBeNull();
  });

  it('rendered actions inherit registry actions', () => {
    const withActions: NotificationTypeDescriptor = {
      ...mention,
      actions: [{ key: 'ack', label_i18n: 'a.ack', method: 'POST',
                  url_template: '/x', style: 'primary' }],
    };
    const r = renderNotif(withActions, { message: 'hi' }, t);
    expect(r.actions).toHaveLength(1);
    expect(r.actions[0].key).toBe('ack');
  });
});
```

- [ ] **Step 2: Run, verify FAIL**

```bash
cd frontend && npx vitest run tests/unit/lib/notifications/renderers.test.ts
```

- [ ] **Step 3: Implement**

`frontend/lib/notifications/registry.ts`:

```ts
/**
 * @file lib/notifications/registry.ts
 * @brief react-query backed mirror of the backend NotificationType registry.
 */
import { useQuery } from '@tanstack/react-query';
import { listTypes } from '@/lib/api/notifications';
import type { NotificationTypeDescriptor } from './types';

export const REGISTRY_KEY = ['notifications', 'types'] as const;

export function useNotificationRegistry() {
  const q = useQuery({
    queryKey: REGISTRY_KEY,
    queryFn: listTypes,
    staleTime: Infinity,
    gcTime: Infinity,
  });
  const map = new Map<string, NotificationTypeDescriptor>(
    (q.data ?? []).map((t) => [t.key, t]),
  );
  return { types: q.data ?? [], byKey: map, isLoading: q.isLoading, error: q.error };
}

export function useNotificationType(key: string): NotificationTypeDescriptor | null {
  const { byKey } = useNotificationRegistry();
  return byKey.get(key) ?? null;
}
```

`frontend/lib/notifications/renderers.ts`:

```ts
/**
 * @file lib/notifications/renderers.ts
 * @brief Per-type renderer with default fallback. Plugins call
 *        registerRenderer(typeKey, fn) to override the default.
 */
import type {
  ActionDescriptor, NotificationTypeDescriptor,
} from './types';

type T = (key: string) => string;

export interface RenderedAction {
  key: string;
  label: string;
  method: ActionDescriptor['method'];
  url: string;
  style: ActionDescriptor['style'];
}

export interface RenderedNotif {
  title: string;
  body: string;
  icon: string;
  link: string | null;
  actions: RenderedAction[];
}

type RenderFn = (
  type: NotificationTypeDescriptor,
  payload: Record<string, unknown>,
  t: T,
) => RenderedNotif;

const _registry = new Map<string, RenderFn>();

export function registerRenderer(typeKey: string, fn: RenderFn): void {
  _registry.set(typeKey, fn);
}

function _interpolate(template: string, payload: Record<string, unknown>): string {
  return template.replace(/\{(\w+)\}/g, (_, k) => String(payload[k] ?? ''));
}

function _defaultRender(
  type: NotificationTypeDescriptor,
  payload: Record<string, unknown>,
  t: T,
): RenderedNotif {
  const body = String(payload.message ?? '');
  const link = typeof payload.link === 'string' ? payload.link : null;
  return {
    title: t(type.label_i18n),
    body,
    icon: type.icon,
    link,
    actions: type.actions.map((a) => ({
      key: a.key,
      label: t(a.label_i18n),
      method: a.method,
      url: _interpolate(a.url_template, payload),
      style: a.style,
    })),
  };
}

export function renderNotif(
  type: NotificationTypeDescriptor,
  payload: Record<string, unknown>,
  t: T,
): RenderedNotif {
  const fn = _registry.get(type.key) ?? _defaultRender;
  return fn(type, payload, t);
}
```

- [ ] **Step 4: Verify PASS**

```bash
cd frontend && npx vitest run tests/unit/lib/notifications/renderers.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/notifications/ frontend/tests/unit/lib/notifications/
git commit -m "feat(notifications): client registry hook + per-type renderers"
```

---

## Task 3: Toast store extensions + Toast component update

**Files:**
- Modify: `frontend/stores/toasts.ts`
- Modify: `frontend/components/ui/Toast.tsx`

- [ ] **Step 1: Failing test**

`frontend/tests/unit/stores/toasts.test.ts`:

```ts
import { describe, it, expect, beforeEach } from 'vitest';
import { useToasts } from '@/stores/toasts';

beforeEach(() => useToasts.getState().clear());

describe('toast store', () => {
  it('dedupes within window when dedupeKey set', () => {
    const id1 = useToasts.getState().push({
      variant: 'info', message: 'a', dedupeKey: 'k1',
    });
    const id2 = useToasts.getState().push({
      variant: 'info', message: 'a', dedupeKey: 'k1',
    });
    expect(id2).toBe(id1);
    expect(useToasts.getState().items).toHaveLength(1);
  });

  it('pushes action button and exposes onClick', () => {
    let clicked = 0;
    useToasts.getState().push({
      variant: 'info', message: 'a',
      action: { label: 'Open', onClick: () => clicked++ },
    });
    const t = useToasts.getState().items[0];
    t.action!.onClick();
    expect(clicked).toBe(1);
  });
});
```

- [ ] **Step 2: Implement store changes**

Modify `frontend/stores/toasts.ts`:

```ts
export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface Toast {
  id: string;
  variant: ToastVariant;
  title?: string;
  message: string;
  ttl?: number | null;
  action?: ToastAction;
  priority?: number;     // higher = sorted earlier
  dedupeKey?: string;
}

interface ToastsState {
  items: Toast[];
  push: (t: Omit<Toast, 'id'>) => string;
  dismiss: (id: string) => void;
  update: (id: string, partial: Partial<Omit<Toast, 'id'>>) => void;
  clear: () => void;
}

const _DEDUPE_WINDOW_MS = 5000;
const _recent = new Map<string, { id: string; at: number }>();

// In `push`:
push: (t) => {
  const now = Date.now();
  if (t.dedupeKey) {
    const seen = _recent.get(t.dedupeKey);
    if (seen && now - seen.at < _DEDUPE_WINDOW_MS) return seen.id;
  }
  const id = (typeof crypto !== 'undefined' && 'randomUUID' in crypto)
    ? crypto.randomUUID()
    : `t_${now}_${Math.random().toString(36).slice(2)}`;
  if (t.dedupeKey) _recent.set(t.dedupeKey, { id, at: now });
  const ttl = t.ttl !== undefined ? t.ttl : getDefaultTtl(t.variant);
  set((s) => {
    const next = [...s.items, { ...t, id, ttl }]
      .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0));
    return { items: next };
  });
  return id;
},
```

Modify `frontend/components/ui/Toast.tsx` — render the action button between the body and the dismiss icon when `toast.action` is set; bump live-region politeness to `assertive` when `variant === 'danger'`.

- [ ] **Step 3: Verify PASS**

```bash
cd frontend && npx vitest run tests/unit/stores/toasts.test.ts
```

- [ ] **Step 4: Commit**

```bash
git add frontend/stores/toasts.ts frontend/components/ui/Toast.tsx frontend/tests/unit/stores/toasts.test.ts
git commit -m "feat(toasts): action button + dedupeKey + priority sort"
```

---

## Task 4: ToastBridge — SSE → auto-toast

**Files:**
- Create: `frontend/components/notifications/ToastBridge.tsx`
- Modify: `frontend/app/app/layout.tsx` (or wherever `<ToastRoot />` lives) to mount `<ToastBridge />`
- Test: `frontend/tests/unit/components/notifications/ToastBridge.test.tsx`

- [ ] **Step 1: Failing test**

`frontend/tests/unit/components/notifications/ToastBridge.test.tsx`:

```tsx
import { render, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useToasts } from '@/stores/toasts';
import { ToastBridge } from '@/components/notifications/ToastBridge';

const onMessageSpies: Array<(data: unknown, type: string) => void> = [];

vi.mock('@/hooks/useSSE', () => ({
  useSSE: (_path: string, opts: { onMessage?: (d: unknown, t: string) => void }) => {
    if (opts.onMessage) onMessageSpies.push(opts.onMessage);
  },
}));

vi.mock('@/lib/notifications/registry', () => ({
  useNotificationRegistry: () => ({
    types: [], byKey: new Map([
      ['mention', { key: 'mention', toast_on_arrival: true,
                    label_i18n: 'notif.mention.label', icon: 'x',
                    actions: [], default_channels: {}, user_configurable: [],
                    group_window_seconds: null, bypass_dnd: false,
                    digestable: true, plugin_id: null, payload_schema: {},
                    category: 'social' }],
      ['reaction', { key: 'reaction', toast_on_arrival: false,
                     label_i18n: 'notif.reaction.label', icon: 'heart',
                     actions: [], default_channels: {}, user_configurable: [],
                     group_window_seconds: 600, bypass_dnd: false,
                     digestable: true, plugin_id: null, payload_schema: {},
                     category: 'social' }],
    ]),
  }),
}));

beforeEach(() => {
  onMessageSpies.length = 0;
  useToasts.getState().clear();
});

const wrap = (ui: React.ReactElement) => {
  const qc = new QueryClient();
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
};

describe('<ToastBridge />', () => {
  it('toasts mention notifications (toast_on_arrival=true)', () => {
    wrap(<ToastBridge />);
    expect(onMessageSpies.length).toBeGreaterThan(0);
    act(() => {
      onMessageSpies[0]({ type: 'mention', payload: { message: 'Hi' } }, 'user_notification');
    });
    expect(useToasts.getState().items).toHaveLength(1);
  });

  it('does not toast reaction (toast_on_arrival=false)', () => {
    wrap(<ToastBridge />);
    act(() => {
      onMessageSpies[0]({ type: 'reaction', payload: { message: 'Like' } }, 'user_notification');
    });
    expect(useToasts.getState().items).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Implement**

`frontend/components/notifications/ToastBridge.tsx`:

```tsx
'use client';
/**
 * @file components/notifications/ToastBridge.tsx
 * @brief Bridges SSE notifications to the toast queue when the type opts in.
 */
import { useTranslations } from 'next-intl';
import { useSSE } from '@/hooks/useSSE';
import { useToasts } from '@/stores/toasts';
import { useNotificationRegistry } from '@/lib/notifications/registry';
import { renderNotif } from '@/lib/notifications/renderers';
import { STREAM_PATH, dismissOne } from '@/lib/api/notifications';

export function ToastBridge() {
  const t = useTranslations();
  const push = useToasts((s) => s.push);
  const { byKey } = useNotificationRegistry();

  useSSE(STREAM_PATH, {
    eventTypes: ['user_notification', 'user_toast'],
    onMessage: (data, _type) => {
      const evt = data as { type: string; payload?: Record<string, unknown>; id?: string };
      const desc = byKey.get(evt.type);
      if (!desc || !desc.toast_on_arrival) return;
      const r = renderNotif(desc, evt.payload ?? {}, t);
      push({
        variant: desc.bypass_dnd ? 'warning' : 'info',
        title: r.title, message: r.body,
        dedupeKey: evt.id ? `notif:${evt.id}` : undefined,
        action: r.link
          ? {
              label: t('notifications.toast.open'),
              onClick: () => {
                if (evt.id) void dismissOne(evt.id).catch(() => {});
                if (r.link) window.location.assign(r.link);
              },
            }
          : undefined,
      });
    },
  });

  return null;
}
```

In `frontend/app/app/layout.tsx` (or wherever `<ToastRoot />` is mounted):

```tsx
import { ToastBridge } from '@/components/notifications/ToastBridge';
...
<ToastRoot />
<ToastBridge />
```

Add i18n key `notifications.toast.open` → "Open".

- [ ] **Step 3: Verify PASS**

```bash
cd frontend && npx vitest run tests/unit/components/notifications/ToastBridge.test.tsx
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/notifications/ToastBridge.tsx frontend/app/ frontend/messages/en.json frontend/tests/unit/components/notifications/ToastBridge.test.tsx
git commit -m "feat(notifications): SSE → toast bridge respecting toast_on_arrival"
```

---

## Task 5: NotifRow

**Files:**
- Create: `frontend/components/notifications/NotifRow.tsx`
- Test: `frontend/tests/unit/components/notifications/NotifRow.test.tsx`

- [ ] **Step 1: Failing test**

`frontend/tests/unit/components/notifications/NotifRow.test.tsx`:

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { NextIntlClientProvider } from 'next-intl';
import { NotifRow } from '@/components/notifications/NotifRow';
import type { NotificationTypeDescriptor } from '@/lib/notifications/types';

vi.mock('@/lib/api/notifications', () => ({
  callAction: vi.fn().mockResolvedValue({ message: 'ok' }),
  dismissOne: vi.fn().mockResolvedValue({ message: 'ok' }),
}));

const wrap = (ui: React.ReactElement) =>
  render(<NextIntlClientProvider messages={{}} locale="en">{ui}</NextIntlClientProvider>);

const type: NotificationTypeDescriptor = {
  key: 'event_invite', category: 'event',
  default_channels: { inapp: true, email: false, push: false, webhook: false, toast: false },
  user_configurable: ['inapp', 'email', 'push', 'toast'],
  group_window_seconds: null, toast_on_arrival: false, bypass_dnd: false,
  digestable: true,
  actions: [
    { key: 'rsvp_yes', label_i18n: 'rsvp.yes', method: 'POST',
      url_template: '/api/v1/events/{target_id}/rsvp', style: 'primary' },
  ],
  label_i18n: 'notif.event_invite.label', icon: 'calendar', plugin_id: null,
  payload_schema: {},
};

describe('<NotifRow />', () => {
  it('renders title + body + action', () => {
    wrap(<NotifRow item={{
      id: 'n1', user_id: 'u', type: 'event_invite',
      payload: { message: 'Alice invited you', target_id: 't1' },
      read_at: null, dismissed_at: null,
      created_at: '2026-05-02T10:00:00Z',
    }} type={type} onDismissed={() => {}} />);
    expect(screen.getByText(/Alice invited you/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /rsvp.yes/i })).toBeInTheDocument();
  });

  it('clicking action calls callAction with key', async () => {
    const { callAction } = await import('@/lib/api/notifications');
    wrap(<NotifRow item={{
      id: 'n1', user_id: 'u', type: 'event_invite',
      payload: { message: 'x', target_id: 't1' },
      read_at: null, dismissed_at: null,
      created_at: '2026-05-02T10:00:00Z',
    }} type={type} onDismissed={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /rsvp.yes/i }));
    await waitFor(() => expect(callAction).toHaveBeenCalledWith('n1', 'rsvp_yes'));
  });
});
```

- [ ] **Step 2: Implement**

`frontend/components/notifications/NotifRow.tsx`:

```tsx
'use client';
/**
 * @file components/notifications/NotifRow.tsx
 * @brief Registry-driven notification row with optional inline actions.
 */
import { useState } from 'react';
import Link from 'next/link';
import Box from '@mui/joy/Box';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';
import { CheckIcon } from '@heroicons/react/24/outline';
import { renderNotif } from '@/lib/notifications/renderers';
import { callAction, dismissOne } from '@/lib/api/notifications';
import type { NotificationItem, NotificationTypeDescriptor } from '@/lib/notifications/types';

export interface NotifRowProps {
  item: NotificationItem;
  type: NotificationTypeDescriptor;
  onDismissed: (id: string) => void;
  selected?: boolean;
  onSelectChange?: (id: string, selected: boolean) => void;
}

export function NotifRow({ item, type, onDismissed, selected, onSelectChange }: NotifRowProps) {
  const t = useTranslations();
  const [pending, setPending] = useState<string | null>(null);
  const r = renderNotif(type, item.payload ?? {}, t);
  const unread = !item.read_at && !item.dismissed_at;

  const handleAction = async (k: string) => {
    setPending(k);
    try {
      await callAction(item.id, k);
      onDismissed(item.id);
    } finally {
      setPending(null);
    }
  };

  const handleAck = async () => {
    setPending('ack');
    try { await dismissOne(item.id); onDismissed(item.id); } finally { setPending(null); }
  };

  const Body = (
    <Stack direction="row" spacing={1.5} alignItems="flex-start"
           sx={{ px: 2, py: 1.5, background: unread ? 'primary.softBg' : 'transparent' }}>
      {onSelectChange && (
        <input type="checkbox" checked={!!selected}
               onChange={(e) => onSelectChange(item.id, e.target.checked)}
               aria-label="Select notification" />
      )}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Typography level="body-xs" color="neutral">
          {new Date(item.created_at).toLocaleString()}
        </Typography>
        <Typography level="body-sm" sx={{ fontWeight: 'lg' }}>{r.title}</Typography>
        <Typography level="body-sm" sx={{ wordBreak: 'break-word' }}>{r.body}</Typography>
        {r.actions.length > 0 && (
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            {r.actions.map((a) => (
              <Button key={a.key} size="sm"
                      variant={a.style === 'primary' ? 'solid' : 'soft'}
                      color={a.style === 'danger' ? 'danger' : 'primary'}
                      loading={pending === a.key}
                      onClick={() => handleAction(a.key)}>
                {a.label}
              </Button>
            ))}
          </Stack>
        )}
      </Box>
      {unread && (
        <IconButton tooltip="Acknowledge" aria-label="Acknowledge notification"
                    size="sm" variant="plain" color="neutral"
                    loading={pending === 'ack'} onClick={handleAck}>
          <CheckIcon aria-hidden width={16} height={16} />
        </IconButton>
      )}
    </Stack>
  );
  return r.link
    ? <Box component={Link} href={r.link} onClick={() => { void dismissOne(item.id); onDismissed(item.id); }}
           sx={{ display: 'block', color: 'inherit', textDecoration: 'none' }}>{Body}</Box>
    : Body;
}
```

- [ ] **Step 3: Verify PASS + commit**

```bash
cd frontend && npx vitest run tests/unit/components/notifications/NotifRow.test.tsx
git add frontend/components/notifications/NotifRow.tsx frontend/tests/unit/components/notifications/NotifRow.test.tsx
git commit -m "feat(notifications): registry-driven NotifRow with inline actions"
```

---

## Task 6: NotificationsBell rewrite (active-only + prune)

**Files:**
- Rewrite: `frontend/components/notifications/NotificationsBell.tsx`
- Modify: `frontend/tests/unit/components/notifications/NotificationsBell.test.tsx`
- Add: button-CTA "View all" emits a custom event consumed by Drawer (Task 7)

- [ ] **Step 1: Failing test**

Replace `frontend/tests/unit/components/notifications/NotificationsBell.test.tsx`:

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import { NotificationsBell } from '@/components/notifications/NotificationsBell';

vi.mock('@/stores/session', () => ({
  useSession: (sel: any) => sel({ status: 'authenticated' }),
}));
vi.mock('@/hooks/useSSE', () => ({ useSSE: vi.fn() }));
vi.mock('@/lib/api/notifications', async () => {
  const actual = await vi.importActual<any>('@/lib/api/notifications');
  return {
    ...actual,
    listActive: vi.fn().mockResolvedValue({ items: [
      { id: 'a', user_id: 'u', type: 'mention', payload: { message: 'A' },
        read_at: null, dismissed_at: null, created_at: '2026-05-02T00:00:00Z' },
    ]}),
    getUnreadCount: vi.fn().mockResolvedValue({ count: 1 }),
    dismissOne: vi.fn().mockResolvedValue({ message: 'ok' }),
    listTypes: vi.fn().mockResolvedValue([
      { key: 'mention', category: 'social',
        default_channels: { inapp: true, email: true, push: true, webhook: false, toast: true },
        user_configurable: ['inapp','email','push','toast'],
        group_window_seconds: null, toast_on_arrival: true, bypass_dnd: false,
        digestable: true, actions: [], label_i18n: 'notif.mention.label',
        icon: 'at-symbol', plugin_id: null, payload_schema: {} },
    ]),
  };
});

const wrap = (ui: React.ReactElement) => {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <NextIntlClientProvider locale="en" messages={{}}>{ui}</NextIntlClientProvider>
    </QueryClientProvider>,
  );
};

describe('<NotificationsBell /> (v2)', () => {
  it('shows badge with unread count and renders active items in popover', async () => {
    wrap(<NotificationsBell />);
    fireEvent.click(await screen.findByRole('button', { name: /Notifications/i }));
    expect(await screen.findByText(/A/)).toBeInTheDocument();
  });

  it('clicking ack removes item from bell list', async () => {
    const { dismissOne } = await import('@/lib/api/notifications');
    wrap(<NotificationsBell />);
    fireEvent.click(await screen.findByRole('button', { name: /Notifications/i }));
    fireEvent.click(await screen.findByRole('button', { name: /Acknowledge notification/i }));
    await waitFor(() => expect(dismissOne).toHaveBeenCalledWith('a'));
  });

  it('"View all" button dispatches drawer-open event', async () => {
    const handler = vi.fn();
    window.addEventListener('notifications:drawer-open', handler);
    wrap(<NotificationsBell />);
    fireEvent.click(await screen.findByRole('button', { name: /Notifications/i }));
    fireEvent.click(await screen.findByRole('button', { name: /View all/i }));
    expect(handler).toHaveBeenCalled();
    window.removeEventListener('notifications:drawer-open', handler);
  });
});
```

- [ ] **Step 2: Rewrite component**

Replace `frontend/components/notifications/NotificationsBell.tsx` — switch query from `listNotifications` to `listActive`; switch ack from `markRead` to `dismissOne`; replace `Row` with `NotifRow` (Task 5) using `useNotificationRegistry().byKey`; add a "View all" `Button` in the popover footer that dispatches `new CustomEvent('notifications:drawer-open')`. Reuse the existing motion/badge/SSE bits unchanged.

- [ ] **Step 3: Verify PASS + commit**

```bash
cd frontend && npx vitest run tests/unit/components/notifications/NotificationsBell.test.tsx
git add frontend/components/notifications/NotificationsBell.tsx frontend/tests/unit/components/notifications/NotificationsBell.test.tsx
git commit -m "feat(notifications): bell shows active-only + dispatches drawer-open"
```

---

## Task 7: NotificationsDrawer

**Files:**
- Create: `frontend/components/notifications/NotificationsDrawer.tsx`
- Modify: `frontend/components/layout/TopBar.tsx` to mount `<NotificationsDrawer />`
- Test: `frontend/tests/unit/components/notifications/NotificationsDrawer.test.tsx`

- [ ] **Step 1: Failing test**

`frontend/tests/unit/components/notifications/NotificationsDrawer.test.tsx`:

```tsx
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import { NotificationsDrawer } from '@/components/notifications/NotificationsDrawer';

vi.mock('@/lib/api/notifications', () => ({
  listNotifications: vi.fn().mockResolvedValue({
    items: [
      { id: 'a', user_id: 'u', type: 'mention', payload: { message: 'A' },
        read_at: null, dismissed_at: null, created_at: '2026-05-02T00:00:00Z' },
      { id: 'b', user_id: 'u', type: 'reaction', payload: { message: 'B' },
        read_at: null, dismissed_at: '2026-05-02T01:00:00Z', created_at: '2026-05-02T00:30:00Z' },
    ],
    next_cursor: null, has_more: false,
  }),
  dismissOne: vi.fn(), markRead: vi.fn(), clearAllNotifications: vi.fn(),
  listTypes: vi.fn().mockResolvedValue([]),
}));

const wrap = (ui: React.ReactElement) => {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <NextIntlClientProvider locale="en" messages={{}}>{ui}</NextIntlClientProvider>
    </QueryClientProvider>,
  );
};

describe('<NotificationsDrawer />', () => {
  it('opens on notifications:drawer-open event and renders both items', async () => {
    wrap(<NotificationsDrawer />);
    act(() => { window.dispatchEvent(new CustomEvent('notifications:drawer-open')); });
    expect(await screen.findByText(/A/)).toBeInTheDocument();
    expect(await screen.findByText(/B/)).toBeInTheDocument();
  });

  it('"Unread" filter hides dismissed item', async () => {
    wrap(<NotificationsDrawer />);
    act(() => { window.dispatchEvent(new CustomEvent('notifications:drawer-open')); });
    fireEvent.click(await screen.findByRole('button', { name: /Unread/i }));
    await waitFor(() => {
      expect(screen.queryByText('B')).not.toBeInTheDocument();
      expect(screen.getByText('A')).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Implement**

`frontend/components/notifications/NotificationsDrawer.tsx`:

```tsx
'use client';
/**
 * @file components/notifications/NotificationsDrawer.tsx
 * @brief Right slide-out: full notification history, filters, bulk actions.
 */
import { useEffect, useMemo, useState } from 'react';
import Box from '@mui/joy/Box';
import Drawer from '@mui/joy/Drawer';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Chip from '@mui/joy/Chip';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { NotifRow } from './NotifRow';
import { listNotifications, dismissOne, markRead, clearAllNotifications } from '@/lib/api/notifications';
import { useNotificationRegistry } from '@/lib/notifications/registry';
import type { NotificationItem } from '@/lib/notifications/types';

type Filter = 'all' | 'unread';

const HISTORY_KEY = ['notifications', 'history'] as const;

export function NotificationsDrawer() {
  const t = useTranslations();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState<Filter>('all');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const { byKey } = useNotificationRegistry();

  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener('notifications:drawer-open', onOpen);
    return () => window.removeEventListener('notifications:drawer-open', onOpen);
  }, []);

  const list = useQuery({
    queryKey: HISTORY_KEY,
    queryFn: () => listNotifications(),
    enabled: open,
  });

  const items: NotificationItem[] = list.data?.items ?? [];
  const filtered = useMemo(() =>
    filter === 'unread'
      ? items.filter((i) => !i.read_at && !i.dismissed_at)
      : items,
    [items, filter],
  );

  const onDismissed = (id: string) => {
    qc.setQueryData<{ items: NotificationItem[] }>(HISTORY_KEY, (prev) =>
      prev ? { ...prev, items: prev.items.map((i) =>
        i.id === id ? { ...i, dismissed_at: new Date().toISOString() } : i) } : prev,
    );
  };

  const bulkDismiss = async () => {
    await Promise.all([...selected].map((id) => dismissOne(id)));
    qc.invalidateQueries({ queryKey: HISTORY_KEY });
    setSelected(new Set());
  };

  return (
    <Drawer anchor="right" open={open} onClose={() => setOpen(false)}
            slotProps={{ content: { sx: { width: { xs: '100%', sm: 480 } } } }}>
      <Stack sx={{ p: 2 }} spacing={2}>
        <Typography level="title-lg">{t('notifications.drawer.title')}</Typography>
        <Stack direction="row" spacing={1}>
          <Button size="sm" variant={filter === 'all' ? 'solid' : 'soft'}
                  onClick={() => setFilter('all')}>{t('notifications.filter.all')}</Button>
          <Button size="sm" variant={filter === 'unread' ? 'solid' : 'soft'}
                  onClick={() => setFilter('unread')}>{t('notifications.filter.unread')}</Button>
        </Stack>
        {selected.size > 0 && (
          <Stack direction="row" spacing={1}>
            <Chip size="sm">{selected.size} selected</Chip>
            <Button size="sm" onClick={bulkDismiss}>{t('notifications.bulk.dismiss')}</Button>
          </Stack>
        )}
        <Box sx={{ overflow: 'auto' }}>
          {list.isLoading && <Typography level="body-sm">…</Typography>}
          {filtered.length === 0 && !list.isLoading && (
            <Typography level="body-sm">{t('notifications.drawer.empty')}</Typography>
          )}
          {filtered.map((n) => {
            const desc = byKey.get(n.type);
            if (!desc) return null;
            return (
              <NotifRow key={n.id} item={n} type={desc} onDismissed={onDismissed}
                        selected={selected.has(n.id)}
                        onSelectChange={(id, sel) => {
                          setSelected((s) => {
                            const next = new Set(s);
                            if (sel) next.add(id); else next.delete(id);
                            return next;
                          });
                        }} />
            );
          })}
        </Box>
      </Stack>
    </Drawer>
  );
}
```

Mount in `frontend/components/layout/TopBar.tsx` after the bell.

Add i18n keys: `notifications.drawer.title` "Notifications", `notifications.drawer.empty` "No notifications.", `notifications.filter.all` "All", `notifications.filter.unread` "Unread", `notifications.bulk.dismiss` "Dismiss selected".

- [ ] **Step 3: Verify PASS + commit**

```bash
cd frontend && npx vitest run tests/unit/components/notifications/NotificationsDrawer.test.tsx
git add frontend/components/notifications/NotificationsDrawer.tsx frontend/components/layout/TopBar.tsx frontend/messages/en.json frontend/tests/unit/components/notifications/NotificationsDrawer.test.tsx
git commit -m "feat(notifications): drawer with filters + bulk dismiss"
```

---

## Task 8: NotificationsTab — registry-driven matrix + DnD + snooze + cadence

**Files:**
- Rewrite: `frontend/components/settings/NotificationsTab.tsx`
- Create: `frontend/components/settings/DnDScheduleEditor.tsx`
- Create: `frontend/components/settings/SnoozeControls.tsx`
- Test: `frontend/tests/unit/components/settings/NotificationsTab.test.tsx`
- Test: `frontend/tests/unit/components/settings/DnDScheduleEditor.test.tsx`

- [ ] **Step 1: Failing tests**

`frontend/tests/unit/components/settings/NotificationsTab.test.tsx`:

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import { NotificationsTab } from '@/components/settings/NotificationsTab';

vi.mock('@/lib/api/notifications', () => ({
  listTypes: vi.fn().mockResolvedValue([
    { key: 'mention', category: 'social',
      default_channels: { inapp: true, email: true, push: true, webhook: false, toast: true },
      user_configurable: ['inapp','email','push','toast'],
      group_window_seconds: null, toast_on_arrival: true, bypass_dnd: false,
      digestable: true, actions: [], label_i18n: 'notif.mention.label',
      icon: 'at-symbol', plugin_id: null, payload_schema: {} },
    { key: 'reaction', category: 'social',
      default_channels: { inapp: true, email: false, push: false, webhook: false, toast: false },
      user_configurable: ['inapp','email','push','toast'],
      group_window_seconds: 600, toast_on_arrival: false, bypass_dnd: false,
      digestable: true, actions: [], label_i18n: 'notif.reaction.label',
      icon: 'heart', plugin_id: null, payload_schema: {} },
  ]),
  getPreferences: vi.fn().mockResolvedValue({
    notification_prefs: { mention: { email: false } },
    dnd_schedule: null, dnd_until: null, dnd_timezone: 'UTC',
    digest_cadence: { reaction: 'daily' },
  }),
  patchPreferences: vi.fn().mockResolvedValue({}),
}));
vi.mock('@/lib/api/webhooks', () => ({ listWebhooks: vi.fn().mockResolvedValue([]) }));
vi.mock('@/hooks/useSettings', () => ({
  useNotificationPrefs: () => ({ data: {}, isLoading: false }),
  useUpdateNotificationPrefs: () => ({ mutate: vi.fn() }),
}));

const wrap = (ui: React.ReactElement) => {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <NextIntlClientProvider locale="en" messages={{}}>{ui}</NextIntlClientProvider>
    </QueryClientProvider>,
  );
};

describe('<NotificationsTab /> v2', () => {
  it('renders one row per registered type', async () => {
    wrap(<NotificationsTab />);
    expect(await screen.findByText(/notif.mention.label/)).toBeInTheDocument();
    expect(await screen.findByText(/notif.reaction.label/)).toBeInTheDocument();
  });

  it('toggle email for mention persists through patchPreferences', async () => {
    const { patchPreferences } = await import('@/lib/api/notifications');
    wrap(<NotificationsTab />);
    const switches = await screen.findAllByRole('checkbox');
    // Find mention's email switch by accessible name; assume label `mention email`
    const emailToggle = switches.find((s) => s.getAttribute('aria-label') === 'mention email');
    fireEvent.click(emailToggle!);
    await waitFor(() => expect(patchPreferences).toHaveBeenCalled());
  });
});
```

- [ ] **Step 2: Rewrite component**

`frontend/components/settings/NotificationsTab.tsx`:

```tsx
'use client';
/**
 * @file components/settings/NotificationsTab.tsx
 * @brief Registry-driven settings: per-type channel matrix + DnD + cadence + webhooks.
 */
import { useEffect, useState } from 'react';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Switch from '@mui/joy/Switch';
import Select from '@mui/joy/Select';
import Option from '@mui/joy/Option';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Card, SettingsRow } from '@/components/ui';
import { PushSubscriptionRow } from './PushSubscriptionRow';
import { SnoozeControls } from './SnoozeControls';
import { DnDScheduleEditor } from './DnDScheduleEditor';
import { WebhookList } from './WebhookList';
import { useNotificationRegistry } from '@/lib/notifications/registry';
import { getPreferences, patchPreferences } from '@/lib/api/notifications';
import type { Channel, PreferencesPayload } from '@/lib/notifications/types';

const PREFS_KEY = ['notifications', 'preferences'] as const;
const CHANNELS: Channel[] = ['inapp', 'email', 'push', 'toast'];
const CADENCES = ['instant', 'hourly', 'daily', 'off'] as const;

export function NotificationsTab() {
  const t = useTranslations();
  const qc = useQueryClient();
  const { types, isLoading: regLoading } = useNotificationRegistry();
  const prefs = useQuery({ queryKey: PREFS_KEY, queryFn: getPreferences });
  const mutate = useMutation({
    mutationFn: patchPreferences,
    onSuccess: (data) => qc.setQueryData(PREFS_KEY, data),
  });
  const [debounced, setDebounced] = useState<Partial<PreferencesPayload>>({});

  useEffect(() => {
    if (!Object.keys(debounced).length) return;
    const id = setTimeout(() => { mutate.mutate(debounced); setDebounced({}); }, 400);
    return () => clearTimeout(id);
  }, [debounced, mutate]);

  if (regLoading || prefs.isLoading || !prefs.data) return <Typography>…</Typography>;
  const p = prefs.data;

  const onChannelToggle = (typeKey: string, ch: Channel, value: boolean) => {
    const merged = {
      ...p.notification_prefs,
      [typeKey]: { ...(p.notification_prefs[typeKey] ?? {}), [ch]: value },
    };
    qc.setQueryData<PreferencesPayload>(PREFS_KEY, { ...p, notification_prefs: merged });
    setDebounced((d) => ({ ...d, notification_prefs: merged }));
  };

  const onCadence = (typeKey: string, cadence: string) => {
    const merged = { ...p.digest_cadence, [typeKey]: cadence as 'instant' | 'hourly' | 'daily' | 'off' };
    qc.setQueryData<PreferencesPayload>(PREFS_KEY, { ...p, digest_cadence: merged });
    setDebounced((d) => ({ ...d, digest_cadence: merged }));
  };

  const grouped = types.reduce<Record<string, typeof types>>((acc, x) => {
    (acc[x.category] ??= []).push(x); return acc;
  }, {});

  return (
    <Stack spacing={3} sx={{ maxWidth: 900 }}>
      <Card variant="outlined">
        <Typography level="title-md">{t('settings.notifications.snooze')}</Typography>
        <SnoozeControls until={p.dnd_until} />
      </Card>

      <Card variant="outlined">
        <Typography level="title-md">{t('settings.notifications.quiet_hours')}</Typography>
        <DnDScheduleEditor
          schedule={p.dnd_schedule} timezone={p.dnd_timezone}
          onChange={(schedule, tz) => {
            qc.setQueryData<PreferencesPayload>(PREFS_KEY,
              { ...p, dnd_schedule: schedule, dnd_timezone: tz });
            setDebounced((d) => ({ ...d, dnd_schedule: schedule, dnd_timezone: tz }));
          }} />
      </Card>

      <PushSubscriptionRow />

      {Object.entries(grouped).map(([cat, list]) => (
        <Card key={cat} variant="outlined">
          <Typography level="title-md">{t(`settings.notifications.cat.${cat}`)}</Typography>
          {list.map((tp) => {
            const userPref = p.notification_prefs[tp.key] ?? {};
            return (
              <SettingsRow key={tp.key} label={t(tp.label_i18n)}
                           description={t('settings.notifications.row.desc')}>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ pt: 0.5 }}>
                  {CHANNELS.filter((c) => tp.user_configurable.includes(c)).map((c) => {
                    const val = userPref[c] ?? tp.default_channels[c] ?? false;
                    return (
                      <Stack key={c} direction="row" spacing={1} alignItems="center" sx={{ flex: 1 }}>
                        <Switch checked={!!val} aria-label={`${tp.key} ${c}`}
                                onChange={(e) => onChannelToggle(tp.key, c, e.target.checked)} />
                        <Typography level="body-sm">{t(`settings.notifications.channel.${c}`)}</Typography>
                      </Stack>
                    );
                  })}
                  {tp.digestable && (
                    <Select size="sm" value={p.digest_cadence[tp.key] ?? 'instant'}
                            onChange={(_, v) => v && onCadence(tp.key, v)}
                            slotProps={{ button: { 'aria-label': `${tp.key} cadence` } }}>
                      {CADENCES.map((c) => (
                        <Option key={c} value={c}>{t(`settings.notifications.cadence.${c}`)}</Option>
                      ))}
                    </Select>
                  )}
                </Stack>
              </SettingsRow>
            );
          })}
        </Card>
      ))}

      <WebhookList />
    </Stack>
  );
}
```

`frontend/components/settings/SnoozeControls.tsx`:

```tsx
'use client';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { snooze, clearSnooze } from '@/lib/api/notifications';
import Stack from '@mui/joy/Stack';
import Chip from '@mui/joy/Chip';
import Typography from '@mui/joy/Typography';
import { Button } from '@/components/ui/Button';
import { useTranslations } from 'next-intl';

export function SnoozeControls({ until }: { until: string | null }) {
  const t = useTranslations();
  const qc = useQueryClient();
  const set = useMutation({ mutationFn: snooze,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications', 'preferences'] }) });
  const clear = useMutation({ mutationFn: clearSnooze,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications', 'preferences'] }) });
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      {until && <Chip color="warning">{t('settings.notifications.snoozed_until', { u: until })}</Chip>}
      <Button size="sm" onClick={() => set.mutate('1h')}>{t('snooze.1h')}</Button>
      <Button size="sm" onClick={() => set.mutate('until_morning')}>{t('snooze.morning')}</Button>
      {until && <Button size="sm" variant="plain" onClick={() => clear.mutate()}>{t('snooze.clear')}</Button>}
    </Stack>
  );
}
```

`frontend/components/settings/DnDScheduleEditor.tsx`:

```tsx
'use client';
/**
 * @file components/settings/DnDScheduleEditor.tsx
 * @brief Weekly schedule editor: per-day windows + tz select.
 */
import { useState, useEffect } from 'react';
import Stack from '@mui/joy/Stack';
import Box from '@mui/joy/Box';
import Typography from '@mui/joy/Typography';
import Input from '@mui/joy/Input';
import Select from '@mui/joy/Select';
import Option from '@mui/joy/Option';
import { Button } from '@/components/ui/Button';
import { useTranslations } from 'next-intl';

const DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const;

type Window = { start: string; end: string };
type Schedule = Record<string, Window[]>;

export interface DnDScheduleEditorProps {
  schedule: Schedule | null;
  timezone: string;
  onChange: (schedule: Schedule, tz: string) => void;
}

export function DnDScheduleEditor({ schedule, timezone, onChange }: DnDScheduleEditorProps) {
  const t = useTranslations();
  const [local, setLocal] = useState<Schedule>(schedule ?? {});
  const [tz, setTz] = useState<string>(timezone);

  useEffect(() => { onChange(local, tz); }, [local, tz, onChange]);

  const addWindow = (day: string) =>
    setLocal((s) => ({ ...s, [day]: [...(s[day] ?? []), { start: '22:00', end: '07:00' }] }));
  const removeWindow = (day: string, idx: number) =>
    setLocal((s) => ({ ...s, [day]: (s[day] ?? []).filter((_, i) => i !== idx) }));
  const editWindow = (day: string, idx: number, field: 'start' | 'end', value: string) =>
    setLocal((s) => ({
      ...s,
      [day]: (s[day] ?? []).map((w, i) => i === idx ? { ...w, [field]: value } : w),
    }));

  const tzOptions = Intl.supportedValuesOf?.('timeZone') ?? ['UTC', 'America/New_York', 'Europe/London'];

  return (
    <Stack spacing={2}>
      <Stack direction="row" alignItems="center" spacing={1}>
        <Typography level="body-sm">{t('settings.notifications.tz')}</Typography>
        <Select value={tz} onChange={(_, v) => v && setTz(v)} size="sm" sx={{ minWidth: 220 }}>
          {tzOptions.slice(0, 200).map((z) => <Option key={z} value={z}>{z}</Option>)}
        </Select>
      </Stack>
      {DAYS.map((day) => (
        <Stack key={day} direction="row" alignItems="center" spacing={1}>
          <Typography sx={{ width: 64 }}>{t(`day.${day}`)}</Typography>
          {(local[day] ?? []).map((w, i) => (
            <Stack key={i} direction="row" alignItems="center" spacing={1}>
              <Input value={w.start} onChange={(e) => editWindow(day, i, 'start', e.target.value)} sx={{ width: 80 }} />
              <Typography>–</Typography>
              <Input value={w.end} onChange={(e) => editWindow(day, i, 'end', e.target.value)} sx={{ width: 80 }} />
              <Button size="sm" variant="plain" onClick={() => removeWindow(day, i)}>×</Button>
            </Stack>
          ))}
          <Button size="sm" variant="plain" onClick={() => addWindow(day)}>+ {t('add')}</Button>
        </Stack>
      ))}
    </Stack>
  );
}
```

`frontend/tests/unit/components/settings/DnDScheduleEditor.test.tsx`:

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { NextIntlClientProvider } from 'next-intl';
import { DnDScheduleEditor } from '@/components/settings/DnDScheduleEditor';

const wrap = (ui: React.ReactElement) =>
  render(<NextIntlClientProvider locale="en" messages={{}}>{ui}</NextIntlClientProvider>);

describe('<DnDScheduleEditor />', () => {
  it('add then remove a window', () => {
    const onChange = vi.fn();
    wrap(<DnDScheduleEditor schedule={{}} timezone="UTC" onChange={onChange} />);
    fireEvent.click(screen.getAllByRole('button', { name: /add/i })[0]);
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ mon: [{ start: '22:00', end: '07:00' }] }),
      'UTC',
    );
  });
});
```

- [ ] **Step 3: Add i18n keys**

In `frontend/messages/en.json` add: `settings.notifications.snooze`, `quiet_hours`, `tz`, `cat.social/event/gallery/prompt/system/plugin`, `row.desc`, `channel.inapp/email/push/toast`, `cadence.instant/hourly/daily/off`, `snooze.1h`, `snooze.morning`, `snooze.clear`, `snoozed_until`, `day.mon..sun`, `add`, plus `notif.<each type>.label`.

- [ ] **Step 4: Verify PASS + commit**

```bash
cd frontend && npx vitest run tests/unit/components/settings/NotificationsTab.test.tsx tests/unit/components/settings/DnDScheduleEditor.test.tsx
git add frontend/components/settings/NotificationsTab.tsx frontend/components/settings/SnoozeControls.tsx frontend/components/settings/DnDScheduleEditor.tsx frontend/messages/en.json frontend/tests/unit/components/settings/
git commit -m "feat(notifications): registry-driven settings + DnD + snooze + cadence"
```

---

## Task 9: WebhookList + WebhookEditModal

**Files:**
- Create: `frontend/components/settings/WebhookList.tsx`
- Create: `frontend/components/settings/WebhookEditModal.tsx`
- Test: `frontend/tests/unit/components/settings/WebhookList.test.tsx`

- [ ] **Step 1: Failing test**

`frontend/tests/unit/components/settings/WebhookList.test.tsx`:

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import { WebhookList } from '@/components/settings/WebhookList';

vi.mock('@/lib/api/webhooks', () => ({
  listWebhooks: vi.fn().mockResolvedValue([
    { id: '1', url: 'https://x.test', type_keys: [],
      enabled: true, failure_count: 0, last_failure_at: null,
      created_at: '2026-05-02T00:00:00Z' },
  ]),
  createWebhook: vi.fn().mockResolvedValue({
    id: '2', url: 'https://y.test', type_keys: [], enabled: true,
    failure_count: 0, last_failure_at: null,
    created_at: '2026-05-02T00:00:00Z', secret: 'sup3r-s3cret',
  }),
  updateWebhook: vi.fn(), deleteWebhook: vi.fn(),
}));

const wrap = (ui: React.ReactElement) => {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <NextIntlClientProvider locale="en" messages={{}}>{ui}</NextIntlClientProvider>
    </QueryClientProvider>,
  );
};

describe('<WebhookList />', () => {
  it('lists existing webhooks', async () => {
    wrap(<WebhookList />);
    expect(await screen.findByText(/x.test/)).toBeInTheDocument();
  });

  it('create flow reveals secret once', async () => {
    wrap(<WebhookList />);
    fireEvent.click(await screen.findByRole('button', { name: /add webhook/i }));
    fireEvent.change(await screen.findByLabelText(/url/i), { target: { value: 'https://y.test' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));
    await waitFor(() => expect(screen.getByText(/sup3r-s3cret/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Implement**

`frontend/components/settings/WebhookList.tsx` + `WebhookEditModal.tsx` — straightforward Card + Modal pattern: list rows from `listWebhooks`; row shows url + type_keys + enabled toggle + delete; "Add webhook" opens `WebhookEditModal` which on save calls `createWebhook`, then displays the returned `secret` in a one-time reveal Alert ("Save this secret now — it will not be shown again."). Edit modal omits the secret reveal.

(Implementation follows the same React/Joy patterns as `PushSubscriptionRow`. Each file ≤ ~180 LOC.)

- [ ] **Step 3: Verify PASS + commit**

```bash
cd frontend && npx vitest run tests/unit/components/settings/WebhookList.test.tsx
git add frontend/components/settings/WebhookList.tsx frontend/components/settings/WebhookEditModal.tsx frontend/tests/unit/components/settings/WebhookList.test.tsx
git commit -m "feat(notifications): webhook list + secret-reveal-on-create modal"
```

---

## Task 10: Multi-tab sync via SSE invalidation

**Files:**
- Modify: `frontend/components/notifications/NotificationsBell.tsx` (handle `user_notification_dismissed`, `user_preferences_updated`)
- Modify: `frontend/components/notifications/NotificationsDrawer.tsx` (same)
- Modify: `frontend/components/settings/NotificationsTab.tsx` (handle `user_preferences_updated`)
- Backend: ensure `services/realtime/events.py` exports `user_notification_dismissed` (Plan A or here)

- [ ] **Step 1: Add SSE handlers**

In each component, add:

```ts
useSSE(STREAM_PATH, {
  enabled: isAuthed,
  eventTypes: ['user_notification_dismissed', 'user_preferences_updated'],
  onMessage: (_data, type) => {
    if (type === 'user_notification_dismissed') {
      qc.invalidateQueries({ queryKey: ['notifications'] });
    }
    if (type === 'user_preferences_updated') {
      qc.invalidateQueries({ queryKey: ['notifications', 'preferences'] });
    }
  },
});
```

- [ ] **Step 2: Backend emits dismiss event**

In `backend/app/services/notification_service.py` `dismiss(...)`, after success, emit via injected `event_bus`. Add `event_bus` to `NotificationService.__init__` (optional). If too invasive, defer to a later micro-task; smoke test still works.

- [ ] **Step 3: Verify + commit**

```bash
cd frontend && npx vitest run tests/unit/components/notifications/
git add frontend/components/notifications/ frontend/components/settings/NotificationsTab.tsx backend/app/services/realtime/events.py backend/app/services/notification_service.py
git commit -m "feat(notifications): multi-tab sync via SSE invalidation"
```

---

## Task 11: E2E + plugin docs

**Files:**
- Create: `frontend/tests/e2e/notifications.spec.ts`
- Create: `docs/plugins/notifications.md`

- [ ] **Step 1: Playwright spec**

`frontend/tests/e2e/notifications.spec.ts`:

```ts
import { test, expect } from '@playwright/test';

test('notif arrives → bell badge → click navigates → bell prunes', async ({ page, request }) => {
  await page.goto('/app');
  // Auth assumed via storageState fixture in playwright.config.ts.
  // Trigger a backend notification via test API helper:
  await request.post('/api/v1/_test/notify', {
    data: { type: 'mention', payload: { message: 'Hello',
      actor_name: 'Tester', target_id: 'post-1', link: '/app/post/post-1' } },
  });
  const bell = page.getByRole('button', { name: /Notifications/i });
  await expect(bell).toBeVisible();
  await expect(page.locator('[data-tour="bell"]')).toContainText('1');
  await bell.click();
  await page.getByText('Hello').click();
  await expect(page).toHaveURL(/post-1/);
  await bell.click();
  await expect(page.getByText('Hello')).toHaveCount(0);
});
```

(Add `/api/v1/_test/notify` to `backend/app/api/v1/_test.py` gated by `ENV=test` only.)

- [ ] **Step 2: Plugin docs**

`docs/plugins/notifications.md`:

````markdown
# Notification types in plugins

Plugins extend the notification system by registering one or more
`NotificationType` values during their package import.

## Minimal example

```python
# my_plugin/notifications.py
from datetime import datetime
from app.services.notifications.registry import (
    register, NotificationType, NotificationPayload, Action,
)


class BookClubMeetingPayload(NotificationPayload):
    book_title: str
    meets_at: datetime


register(NotificationType(
    key="bookclub.meeting_reminder",
    category="plugin",
    payload_schema=BookClubMeetingPayload,
    default_channels={"inapp": True, "email": True, "push": True, "toast": True},
    bypass_dnd=False,
    actions=(
        Action(key="ack", label_i18n="bookclub.notif.ack",
               method="POST",
               url_template="/api/v1/plugins/bookclub/meetings/{target_id}/ack"),
    ),
    label_i18n="bookclub.notif.meeting_reminder",
    icon="book-open",
    plugin_id="bookclub",
))
```

Registering once gives the plugin: settings UI row, all four channels with
user-controllable preferences, group/DnD/digest/webhook fanout, and inline
actions in bell + drawer + toast.

## Frontend renderer override (optional)

```ts
import { registerRenderer } from '@/lib/notifications/renderers';
registerRenderer('bookclub.meeting_reminder', (type, payload, t) => ({
  title: t('bookclub.notif.title', { book: payload.book_title }),
  body: t('bookclub.notif.body', { at: payload.meets_at }),
  icon: 'book-open',
  link: `/plugins/bookclub/meetings/${payload.target_id}`,
  actions: type.actions.map((a) => ({
    key: a.key, label: t(a.label_i18n), method: a.method,
    url: a.url_template.replace('{target_id}', String(payload.target_id)),
    style: a.style,
  })),
}));
```

## Adding a custom channel

```python
from app.services.notifications.channels.base import Channel, ChannelResult
from app.core.dependencies import get_notification_dispatcher


class SmsChannel:
    key = "sms"
    async def send(self, notification) -> ChannelResult:
        # ... talk to your SMS vendor ...
        return ChannelResult(ok=True)


# Register at app boot:
get_notification_dispatcher().register_channel(SmsChannel())
```

Channels are isolated: a failure in one channel does not block others.
````

- [ ] **Step 3: Run E2E + commit**

```bash
cd frontend && npx playwright test tests/e2e/notifications.spec.ts
git add frontend/tests/e2e/notifications.spec.ts docs/plugins/notifications.md backend/app/api/v1/_test.py
git commit -m "test(notifications): e2e + plugin docs"
```

---

## Task 12: Plan-C smoke

- [ ] **Step 1: Frontend full suite + build**

```bash
cd frontend && npx vitest run --coverage && npx eslint . && npx prettier --check . && npx tsc --noEmit && npm run build
```
Expected: green; coverage ≥ pre-Plan-C baseline.

- [ ] **Step 2: Manual UI smoke** (run `scripts/dev-start.sh`)
- Open app → notification arrives via SSE → mention toasts; reaction does not.
- Click bell → see active items only. Click an item → navigates and bell prunes it.
- Open drawer (View all). Filter Unread → only unread. Bulk-select two → Dismiss → both disappear from active query, remain in history.
- Settings → toggle email off for `mention` → verify in DB `notification_prefs.mention.email = false`.
- Settings → set DnD 22:00–07:00 in your tz → trigger mention during window → in-app row exists, no toast/email/push.
- Snooze 1h → trigger mention → same. Clear snooze → next mention toasts again.
- Set `digest_cadence.reaction = "hourly"` → reaction events queue, no email; after beat tick → digest email lands.
- Webhook: add receiver pointed at https://webhook.site → trigger mention → receiver gets HMAC-signed POST. Disable → no further deliveries.

- [ ] **Step 3: Commit any cleanup**

```bash
git add -A && git diff --cached --quiet || git commit -m "chore(notifications): plan-C smoke + cleanup"
```

---

## Self-Review

- **Spec coverage (Plan C scope):** §9.1 component tree (Bell/Drawer/NotifRow/ToastBridge/NotificationsTab) — Tasks 4–9; §9.2 state stores — Tasks 3 & 7; §9.3 renderers — Task 2; §9.4 multi-tab sync — Task 10; §9.5 a11y — `aria-live` (existing) + `aria-label`s in Tasks 5/8 + drawer focus trap (Joy `Drawer` default) + toast `assertive` for danger (Task 3); §9.6 empty / error states — Task 7 (`drawer.empty` key) + bell error path retained from existing component; §12.4 smoke — Task 12; §15 plugin example — Task 11 docs.
- **Placeholder scan:** `WebhookEditModal` body is described prosely, not coded. Acceptable because Task 9's WebhookList test asserts the create-flow secret reveal; the modal implementation should mirror `PushSubscriptionRow`'s pattern (already in repo). If the executor needs a literal skeleton, expand Task 9 Step 2 with the same shape used in `PushSubscriptionRow`.
- **Type consistency:** `NotificationItem` has the same shape across registry, API client, and components (Task 1). `RenderedNotif` shape consistent across `NotifRow`, `ToastBridge`, and renderer tests. Channel union type matches backend (`'inapp' | 'email' | 'push' | 'webhook' | 'toast'`).

---

## Execution Handoff

Plan C complete and saved to `docs/superpowers/plans/2026-05-02-notifications-plan-c-ux-and-extensions.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task
2. **Inline Execution** — executing-plans, batch with checkpoints

Which approach?
