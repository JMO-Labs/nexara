# PR 5 — Mobile PWA + OS notifications

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Installable app that feels native; real, stacked, deep-linked OS notifications with badge.
**Spec:** `00-overview.md` (Q7, Q8). **Branch:** `feat/plat-5-pwa` from `feat/plat-4-sso`. Tasks 1 ∥ 2, then 3, 4.

---

### Task 1: PWA shell

**Files:**
- Modify: `frontend/public/manifest.webmanifest`, `frontend/public/sw.js`, `frontend/app/layout.tsx`, `frontend/components/layout/ServiceWorkerRegistrar.tsx`, `frontend/components/layout/TopBar.tsx`, `frontend/components/notifications/ToastBridge.tsx`, `frontend/components/wishlists/ShipToCard.tsx`, `frontend/components/ui/Markdown.tsx`, `PostsTab.tsx`/`GroupMosaic.tsx` retry
- Create: `frontend/components/layout/InstallPrompt.tsx`, `frontend/components/layout/UpdatePrompt.tsx`, `frontend/public/icons/maskable-512.png` (generated from brand mark with 20 % padding)
- Test: `frontend/tests/unit/layout/{InstallPrompt,UpdatePrompt}.test.tsx`, `frontend/tests/unit/sw.test.ts` (load sw.js in a fake `self`)

**Interfaces:**
- Manifest: `id: "/app"`, theme `#0D1117`, separate `purpose:"any"` and `purpose:"maskable"` icons, `shortcuts`: New post `/app?compose=1`, Chat `/app/chat`, Calendar `/app/calendar`.
- `metadata.icons.apple = "/icons/apple-touch-icon.png"`; TopBar `padding-top: env(safe-area-inset-top)`.
- sw.js: `VERSION` injected at build (`next.config` writes `public/sw-version.js` with git sha; sw `importScripts('/sw-version.js')`); cache-first for `/_next/static/*` and fonts; network-first navigations stored (max 30 entries, LRU); API never cached; remove unconditional `skipWaiting`, handle `message {type:"SKIP_WAITING"}`.
- UpdatePrompt: on `registration.waiting` show toast "New version available" + "Reload" → postMessage SKIP_WAITING → reload on `controllerchange`.
- InstallPrompt: captures `beforeinstallprompt`; dismissible card in More sheet + one-time banner after 3rd visit (localStorage, try/catch); iOS Safari non-standalone → sheet with steps "Tap Share, then Add to Home Screen". Hidden when `matchMedia('(display-mode: standalone)')`.
- Offline: navigations offline show cached page with top banner "You're offline. Showing saved pages."; mutations disabled via `navigator.onLine` hook `useOnline()` on composer submit buttons ("You're offline").
- Internal links: ToastBridge uses `router.push`; ShipToCard `Link`; Markdown internal (`/app/…` or same origin) → `Link` without `target`; retry → `queryClient.invalidateQueries`.
- [ ] Tests: install prompt hidden in standalone; iOS UA shows steps; waiting SW shows Reload and posts SKIP_WAITING; sw caches `/_next/static/a.js` cache-first; Markdown same-origin link has no `target`.
- [ ] Implement → PASS → commit `feat(pwa): install, update prompt, offline pages, safe areas`

---

### Task 2: Push backend quality

**Files:**
- Create: `backend/alembic/versions/0072_push_devices.py`
- Modify: `backend/app/models/push_subscription.py` (whatever file defines it) `+ name text, user_agent text, last_used_at`, `backend/app/services/push_service.py` (404 also deletes; delete dead `should_send_push`/`PUSH_PREF_MAP`), `backend/app/services/notifications/channels/push.py`, `backend/app/api/v1/push.py` (`GET /push/devices`, `PATCH/DELETE /push/devices/{id}`), `deploy/.env.example` (VAPID keys + generate command `npx web-push generate-vapid-keys`)
- Test: `backend/tests/unit/services/test_push_payload.py`

**Interfaces:**
- Payload `{title, body, url, tag, badge_count}`: title/body from notification registry render (same text as in-app list), e.g. title `"Maya Chen"`, body `"commented on your post"`; `tag = f"{type}:{thread_id}"` (post id / channel id / event id, else type); `badge_count` = unread in-app count.
- Device default name parsed from UA (reuse PR 1 `device` parser).
- [ ] Tests: comment notification payload title is actor name, body is rendered text, tag `comment:{post_id}`; 404 from push endpoint deletes subscription; devices list only own.
- [ ] Implement → PASS → commit `feat(push): readable, stacked notifications and per-device management`

---

### Task 3: Client notifications

**Files:**
- Modify: `frontend/public/sw.js` (push → `showNotification(title,{body,tag,data:{url},badge:'/icons/badge-72.png',renotify:true})`, `navigator.setAppBadge?.(badge_count)`; click → focus visible client whose URL matches, else any client + `postMessage({type:'navigate',url})`, else `openWindow(url)`), `frontend/hooks/usePushNotifications.ts` (`isSubscribed` = this device's endpoint in `/push/devices`), `frontend/components/settings/PushSubscriptionRow.tsx` → `PushDevices.tsx`
- Create: `frontend/components/layout/SwNavigateBridge.tsx` (listens for `navigate` → `router.push`), `frontend/components/notifications/ForegroundNotifier.tsx`, `frontend/hooks/useAppBadge.ts`
- Test: `frontend/tests/unit/notifications/ForegroundNotifier.test.tsx`, `frontend/tests/unit/settings/PushDevices.test.tsx`

**Interfaces:**
- ForegroundNotifier: on SSE notification event, if `document.visibilityState === "hidden"` and `Notification.permission === "granted"` and this device has no push subscription → `registration.showNotification` (same tag rules).
- `useAppBadge(unread)` → `setAppBadge(unread)` / `clearAppBadge()` when 0.
- PushDevices: list with "This device" marker, rename inline, remove; iOS non-standalone: "On iPhone, add Nexara to your Home Screen first to get notifications."
- [ ] Tests: hidden tab + no push → showNotification called once with tag; visible tab → not called; device with push → not called; second device shows "Turn on for this device" not "Active".
- [ ] Implement → PASS → commit `feat(notifications): OS notifications, app badge, deep links, device list`

---

### Task 4: Polish PR 5
- [ ] Full suites + build; Lighthouse PWA audit via `npx lighthouse http://localhost:8090/app --only-categories=pwa,accessibility` (score notes in PR); phone screenshots 375×812 + 412×915 + tablet 820×1180 (Playwright) of home, chat, settings; live push via Chrome Playwright with granted permission; PR "Platform 5: mobile app and notifications".
