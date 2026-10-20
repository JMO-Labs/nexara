# Frontend Overhaul P1 — Foundation + Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rip out MUI Joy/Emotion and dead deps, stand up Tailwind v4 + shadcn with the Garden Club tokens, rebuild `components/ui/*`, and ship the new phone/desktop shell.

**Architecture:** Full replacement on `feat/frontend-overhaul`. CSS variables in `app/globals.css` are the single token source; Tailwind `@theme` maps them; shadcn components live in `components/ui/` and keep today's barrel export names so later phases migrate call sites with minimal churn. Shell = `SideNav` (≥ md) + `BottomTabBar`/`MoreSheet` (< md) + `TopBar`, all driven by one `navItems.tsx`.

**Tech Stack:** Next.js 16.2.4 App Router, React 19, Tailwind CSS v4 (`@tailwindcss/postcss`), shadcn/ui (Radix), `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`, next-themes, framer-motion (kept), Vitest 4 + Testing Library.

**Spec:** `docs/superpowers/specs/2026-10-20-frontend-overhaul-design.md` · **Index:** `docs/superpowers/plans/2026-10-20-frontend-overhaul-index.md`

## Global Constraints

- All work under `frontend/`. Run commands from `frontend/`.
- Files ≤ 400 lines. Doxygen header (`@file`, `@brief`) on every new file; `@param`/`@return` on exported functions.
- Hanken Grotesk only, weights 400/600/900. No Fraunces/Geist.
- Tokens exactly per spec §5 table (light + dark). Dark mode = `.dark` class via next-themes `attribute="class"`, `defaultTheme="system"`.
- Icons: `lucide-react` only.
- Sentence case copy; no all-caps labels; no `→` in button text.
- Motion only in response to user action; every animation guarded by `prefers-reduced-motion` (`motion-safe:` / `useReducedMotion`). No page-entrance animation.
- WCAG 2.1 AA: text 4.5:1, large text/UI 3:1; visible focus ring = 2px `accent` outline with 2px offset; every icon-only control has `aria-label`.
- Phase gate (per spec §8): tests touched in this phase + `npx eslint <touched paths>` pass. Full `tsc`/build may stay red (un-migrated pages still import Joy).
- Conventional Commits, ≤72-char subject, no emojis, end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Theme flash / wrong scheme on first paint** — reload in dark OS mode must not flash light. Test in Task 3 (`suppressHydrationWarning` + next-themes class on `<html>`; assert provider attribute is `class`).
2. **Keyboard-only users on desktop side nav** — Tab into nav must expand labels; Esc/blur collapses. Test in Task 8.
3. **Bottom tab bar covering content / iPhone home indicator** — content needs bottom padding = bar height + `env(safe-area-inset-bottom)`. Test in Task 10 (class present on `<main>`).
4. **Non-admin sees Admin entry** — hidden in side nav and More sheet. Tests in Tasks 8 and 9.
5. **Token contrast regressions** when someone edits a hex — Task 2's contrast test fails the build.

---

### Task 0: Precondition — merge in-flight work and branch

**Files:** none (git only)

- [ ] **Step 1:** Ask the user to confirm the ~50 uncommitted files on `polish/phase-5-motion` are ready to commit. Do not proceed without a yes.
- [ ] **Step 2:** On confirmation, commit them (conventional message describing the WIP), push, and merge `polish/phase-5-motion` → `main` per the user's usual flow (MR on GitLab). Wait for merge.
- [ ] **Step 3:** `git checkout main && git pull && git checkout -b feat/frontend-overhaul && git checkout -b feat/fo-p1-foundation-shell`
  Expected: on `feat/fo-p1-foundation-shell`, clean tree.

---

### Task 1: Remove Joy/Emotion/dead deps, install Tailwind + shadcn base

**Files:**
- Modify: `package.json`, `package-lock.json`
- Create: `postcss.config.mjs`, `components.json`, `lib/utils.ts`
- Delete: `theme/joy-theme.ts`, `theme/EmotionRegistry.tsx`, `theme/tokens.ts` (old), `theme/fonts.ts`
- Test: `tests/unit/lib/utils.test.ts`

**Interfaces:**
- Produces: `cn(...inputs: ClassValue[]): string` in `lib/utils.ts` (clsx + tailwind-merge). Every later component uses it.

- [ ] **Step 1: Write failing test** `tests/unit/lib/utils.test.ts`

```ts
import { cn } from '@/lib/utils';
test('cn merges and dedupes tailwind classes', () => {
  expect(cn('px-2', 'px-4', false && 'hidden', 'text-ink')).toBe('px-4 text-ink');
});
```

- [ ] **Step 2:** `npx vitest run tests/unit/lib/utils.test.ts` → FAIL (module not found).
- [ ] **Step 3:** Uninstall: `npm rm @mui/joy @mui/material @emotion/cache @emotion/react @emotion/server @emotion/styled @heroicons/react react-slick slick-carousel @types/react-slick react-grid-layout`. Also remove any `@mui/*` left in `package.json` and any slick CSS imports in `app/globals.css`.
- [ ] **Step 4:** Install: `npm i tailwindcss@^4 @tailwindcss/postcss lucide-react class-variance-authority clsx tailwind-merge`. Create `postcss.config.mjs` with plugin `@tailwindcss/postcss`. Run `npx shadcn@latest init` (style: new-york, base color: neutral, CSS variables: yes, css file `app/globals.css`, components alias `@/components/ui`, utils `@/lib/utils`). Keep the generated `lib/utils.ts` `cn`.
- [ ] **Step 5:** Delete the four `theme/*` files listed above.
- [ ] **Step 6:** `npx vitest run tests/unit/lib/utils.test.ts` → PASS.
- [ ] **Step 7:** Commit `chore(frontend): drop joy/emotion and dead deps, add tailwind v4 + shadcn`.

---

### Task 2: Garden Club tokens + contrast guard

**Files:**
- Create: `theme/palette.ts`, `lib/contrast.ts`
- Modify: `app/globals.css` (replace entire contents)
- Test: `tests/unit/theme/palette.test.ts`

**Interfaces:**
- Produces: `palette: { light: Record<TokenName, string>; dark: Record<TokenName, string> }` and `type TokenName = 'bg'|'surface'|'surface-strong'|'ink'|'accent'|'sun'|'leaf'|'muted'` in `theme/palette.ts`.
- Produces: `contrastRatio(fg: string, bg: string): number` in `lib/contrast.ts` (WCAG 2.1 relative luminance, hex `#RRGGBB` input). Reused by P6 Branding accent validator.
- Produces Tailwind utilities: `bg-bg`, `bg-surface`, `bg-surface-strong`, `text-ink`, `bg-accent`, `text-accent`, `bg-sun`, `bg-leaf`, `text-muted`, `ring-accent`, `font-sans`, plus shadcn semantic vars (`--background`, `--foreground`, `--primary`, `--ring`, …) mapped onto these.

- [ ] **Step 1: Write failing test** `tests/unit/theme/palette.test.ts`

```ts
import { palette } from '@/theme/palette';
import { contrastRatio } from '@/lib/contrast';

test('contrastRatio known pair', () => {
  expect(contrastRatio('#000000', '#FFFFFF')).toBeCloseTo(21, 0);
});

test.each(['light', 'dark'] as const)('%s palette meets AA', (mode) => {
  const p = palette[mode];
  expect(contrastRatio(p.ink, p.bg)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.ink, p.surface)).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.accent, p['surface-strong'])).toBeGreaterThanOrEqual(4.5);
  expect(contrastRatio(p.muted, p['surface-strong'])).toBeGreaterThanOrEqual(3);
});

test('forest text on lilac fill meets AA', () => {
  expect(contrastRatio(palette.light['surface-strong'], palette.light.accent)).toBeGreaterThanOrEqual(4.5);
});
```

- [ ] **Step 2:** Run → FAIL (modules missing).
- [ ] **Step 3:** Write `theme/palette.ts` with the exact hexes from spec §5 table. Write `lib/contrast.ts`.
- [ ] **Step 4:** Rewrite `app/globals.css`: `@import "tailwindcss";`, `@custom-variant dark (&:where(.dark, .dark *));`, `:root { --nx-bg: #E9F1E4; … }`, `.dark { --nx-bg: #0E1F15; … }` (same hexes as `palette.ts`), `@theme inline` mapping `--color-bg: var(--nx-bg)` etc., shadcn vars (`--background: var(--nx-bg)`, `--foreground: var(--nx-ink)`, `--card: var(--nx-surface)`, `--primary: var(--nx-surface-strong)`, `--primary-foreground: var(--nx-accent)`, `--accent: var(--nx-accent)`, `--ring: var(--nx-accent)`, `--radius: 1.25rem`), `--font-sans: var(--font-hanken)`. Base layer: `body { @apply bg-bg text-ink font-sans antialiased; }`, `:focus-visible { outline: 2px solid var(--nx-accent); outline-offset: 2px; }`, and `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; } }`. Add utility `.corner-leaf { border-radius: 1.75rem 1.75rem 1.75rem .375rem; }` (signature featured-card shape).
- [ ] **Step 5:** Run → PASS. If an AA assertion fails, adjust only that token's hex minimally until it passes, and update spec §5 table to match in the same commit.
- [ ] **Step 6:** Commit `feat(frontend): garden club tokens with AA contrast guard`.

---

### Task 3: Font, root layout, providers

**Files:**
- Create: `theme/font.ts`
- Modify: `app/layout.tsx`, `app/providers.tsx`
- Test: `tests/unit/app/providers.test.tsx`

**Interfaces:**
- Produces: `hanken` (`next/font/google` `Hanken_Grotesk`, `weight: ['400','600','900']`, `variable: '--font-hanken'`, `display: 'swap'`, `subsets: ['latin']`).
- Providers tree becomes: `NextThemesProvider(attribute="class", defaultTheme="system", enableSystem, disableTransitionOnChange)` → `NextIntlClientProvider` → `QueryClientProvider`. QueryClient options unchanged.

- [ ] **Step 1: Write failing test** — mock `next-themes` `ThemeProvider` to capture props; render `<Providers><p>hi</p></Providers>`; assert `hi` visible and captured `attribute === 'class'` and `defaultTheme === 'system'`; assert no module under `@mui` is imported (`vi.mock` not needed — simply importing must not throw after Task 1).
- [ ] **Step 2:** Run `npx vitest run tests/unit/app/providers.test.tsx` → FAIL.
- [ ] **Step 3:** Implement. `app/layout.tsx`: remove `InitColorSchemeScript` and old fonts, `className={hanken.variable}` on `<html suppressHydrationWarning>`, `themeColor` light `#E9F1E4` / dark `#0E1F15`, description `'A private home for your family and friends.'`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(frontend): hanken grotesk + class-based theme providers`.

---

### Task 4: Form primitives — Button, IconButton, Input, Textarea, Select

**Files:**
- Rewrite: `components/ui/Button.tsx`, `IconButton.tsx`, `Input.tsx`, `Textarea.tsx`, `Select.tsx`
- Rewrite tests: `tests/unit/ui/Button.test.tsx`, `IconButton.test.tsx`, `Input.test.tsx`; create `Select.test.tsx`

**Interfaces (Produces):**
- `Button`: `React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary'|'secondary'|'ghost'|'outline'|'destructive'; size?: 'sm'|'md'|'lg'; loading?: boolean; asChild?: boolean }`. Default `primary` (`bg-surface-strong text-accent`), `md`. `loading` → `disabled` + `aria-busy="true"` + spinner (Lucide `Loader2`, `motion-safe:animate-spin`). Export `buttonVariants` (cva).
- `IconButton`: same variants; `size?: 'sm'|'md'|'lg'`; **required** `'aria-label': string`; round (`rounded-full`).
- `Input`, `Textarea`: native props + `label?: string; error?: string; hint?: string`. Label linked via `useId`; `error` sets `aria-invalid` and `aria-describedby` to the error text id.
- `Select`: Radix Select. `Select` props `{ value?: string; defaultValue?: string; onValueChange?: (v: string) => void; placeholder?: string; label?: string; disabled?: boolean; children: ReactNode }`. `Option` = `{ value: string; children: ReactNode }` (wraps `SelectItem`).

Steps (same cycle for each component: failing test → run FAIL → implement via `npx shadcn@latest add button input textarea select` then adapt to the interface above → run PASS):

- [ ] **Step 1:** Tests, assertions to include:
  - Button: renders text; `variant="destructive"` has class containing `destructive`; `loading` → `toBeDisabled()` and `aria-busy="true"`; click fires handler.
  - IconButton: `getByRole('button', { name: 'Close' })` when `aria-label="Close"`.
  - Input: `getByLabelText('Email')`; with `error="Required"` → `toHaveAttribute('aria-invalid','true')` and `toHaveAccessibleDescription('Required')`.
  - Select: open via keyboard (`user.keyboard('{Enter}')` on trigger), choose option "Weekly" → `onValueChange('weekly')`.
- [ ] **Step 2:** `npx vitest run tests/unit/ui/Button.test.tsx tests/unit/ui/IconButton.test.tsx tests/unit/ui/Input.test.tsx tests/unit/ui/Select.test.tsx` → FAIL.
- [ ] **Step 3:** Implement the five components to the interfaces above.
- [ ] **Step 4:** Same command → PASS.
- [ ] **Step 5:** Commit `feat(ui): tailwind form primitives`.

---

### Task 5: Overlay primitives — Modal, Drawer, Tooltip, Toast, ConfirmDialog

**Files:**
- Rewrite: `components/ui/Modal.tsx`, `Drawer.tsx`, `Tooltip.tsx`, `Toast.tsx`, `ConfirmDialog.tsx`
- Rewrite tests: `tests/unit/ui/Toast.test.tsx`, `Tooltip.test.tsx`; create `Modal.test.tsx`, `Drawer.test.tsx`

**Interfaces (Produces):**
- `Modal`: `{ open: boolean; onClose: () => void; title: string; description?: string; children: ReactNode; footer?: ReactNode; size?: 'sm'|'md'|'lg' }` — Radix Dialog; on phones (< md) renders full-width bottom-anchored sheet, ≥ md centered.
- `Drawer`: `{ open: boolean; onClose: () => void; title: string; side?: 'left'|'right'|'bottom'; children: ReactNode }` — shadcn `sheet` (Radix Dialog). `MoreSheet` (Task 7) uses `side="bottom"`.
- `Tooltip`: `{ content: ReactNode; children: ReactElement; side?: 'top'|'right'|'bottom'|'left' }` — Radix Tooltip; wrap app once in `TooltipProvider` inside `Shell` (Task 9). Export `TooltipProvider`.
- `ToastRoot`: keep reading the existing `stores/toasts` zustand store (do not add a toast library); render list in `aria-live="polite"` region, bottom-center on phones above tab bar, bottom-right ≥ md.
- `ConfirmDialog`: keep existing `stores/confirmDialog` API; render via `Modal`.

- [ ] **Step 1:** Tests:
  - Modal: `open` → `getByRole('dialog', { name: title })`; `Escape` calls `onClose`; focus moves inside dialog.
  - Drawer: same, with `side="bottom"`.
  - Tooltip: hover/focus trigger → `findByRole('tooltip')` has content.
  - Toast: pushing a toast via store renders its text inside `role="status"` region; dismiss button (`aria-label="Dismiss"`) removes it.
- [ ] **Step 2:** Run those four test files → FAIL.
- [ ] **Step 3:** `npx shadcn@latest add dialog sheet tooltip`; implement wrappers to the interfaces.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(ui): radix overlay primitives`.

---

### Task 6: Display primitives — Card, Badge/Chip, Avatar, Skeleton, EmptyState, Tabs, SettingsRow, Collapsible, Carousel, Markdown, ScopeSelect

**Files:**
- Rewrite: the matching files in `components/ui/`
- Delete: `components/ui/CommandPalette.tsx`, `tests/unit/ui/CommandPalette.test.tsx` (spec §9: keep `search/GlobalCommandPalette.tsx`)
- Rewrite tests: `EmptyState.test.tsx`, `Skeleton.test.tsx`, `SettingsRow.test.tsx`, `ScopeSelect.test.tsx`; create `Tabs.test.tsx`, `Card.test.tsx`
- Modify: `components/ui/index.ts`

**Interfaces (Produces):**
- `Card`: `HTMLAttributes<HTMLDivElement> & { tone?: 'default'|'featured' }`. `default` = `bg-surface rounded-[1.25rem]`; `featured` = `bg-surface-strong text-bg corner-leaf`.
- `Badge`: `{ tone?: 'neutral'|'accent'|'sun'|'leaf'; children }`. `Chip`: Badge + optional `onRemove?: () => void` (remove button `aria-label="Remove {children}"`).
- `Avatar`: `{ src?: string; name: string; size?: 'sm'|'md'|'lg' }` — initials fallback from `name`; `alt={name}`. `AvatarGroup`: `{ max?: number; children }` shows `+N`.
- `Tabs`, `TabList`, `Tab`, `TabPanel` = aliases of shadcn `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` (Radix; `value`-based, not index-based).
- `Skeleton`, `EmptyState` (`{ title: string; description?: string; action?: ReactNode; icon?: LucideIcon }`), `SettingsRow`, `Collapsible` (Radix), `Carousel` (embla), `Markdown`, `ScopeSelect`: keep current public props; restyle only.
- `index.ts`: same export names as today minus `CommandPalette`/`CommandItem`/`CommandPaletteProps`; add `TooltipProvider`, `ConfirmDialog`, `Collapsible`, `Carousel`.

- [ ] **Step 1:** Tests:
  - Card `tone="featured"` has class `corner-leaf`.
  - Tabs: arrow-right moves focus to next `tab`; selecting shows matching `tabpanel`.
  - EmptyState renders title as heading and the action.
  - Existing ScopeSelect/SettingsRow/Skeleton behavior assertions kept, Joy-class assertions removed.
- [ ] **Step 2:** Run `npx vitest run tests/unit/ui` → FAIL.
- [ ] **Step 3:** `npx shadcn@latest add card badge avatar skeleton tabs collapsible`; implement.
- [ ] **Step 4:** `npx vitest run tests/unit/ui` → PASS (all ui tests).
- [ ] **Step 5:** Commit `feat(ui): display primitives, single command palette`.

---

### Task 7: Nav model

**Files:**
- Rewrite: `components/layout/navItems.tsx`
- Test: `tests/unit/layout/navItems.test.ts`

**Interfaces (Produces):**
- `type NavItem = { label: string; href: string; Icon: LucideIcon; adminOnly?: boolean }`
- `PRIMARY_NAV: NavItem[]` — exactly, in order: Home `/app` `House`; Chat `/app/chat` `MessageCircle`; Calendar `/app/events` `CalendarDays`; Groups `/app/subgroups` `Users`.
- `MORE_NAV: NavItem[]` — in order: Galleries `/app/galleries` `Images`; Media `/app/media` `Film`; Members `/app/members` `Contact`; Notifications `/app/notifications` `Bell`; Settings `/app/settings` `Settings`; Admin `/app/admin` `ShieldCheck` `adminOnly: true`; Help `/app/help` `CircleHelp`.
- `visibleNav(items: NavItem[], isAdmin: boolean): NavItem[]`
- `isNavActive(pathname: string, href: string): boolean` — unchanged behavior.

- [ ] **Step 1:** Test: labels of `PRIMARY_NAV` equal `['Home','Chat','Calendar','Groups']`; `visibleNav(MORE_NAV,false)` excludes `Admin`, `true` includes; `isNavActive('/app/chat/abc','/app/chat')` true, `isNavActive('/app/chat','/app')` false.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(layout): lucide nav model with primary/more split`.

Note: `/app/notifications` and `/app/help` routes arrive in P7/P6; links may 404 until then.

---

### Task 8: SideNav (desktop)

**Files:**
- Create: `components/layout/SideNav.tsx`
- Delete: `components/layout/Sidebar.tsx`, `tests/unit/layout/Sidebar.test.tsx`, `sidebarCollapsed`/`toggleSidebar`/`setSidebarCollapsed` from `stores/ui.ts` (and their `partialize` entry)
- Test: `tests/unit/layout/SideNav.test.tsx`

**Interfaces:**
- Consumes: `PRIMARY_NAV`, `MORE_NAV`, `visibleNav`, `isNavActive` (Task 7); `useSession` for `isAdmin` (read existing user role field from `stores/session.ts`).
- Produces: `SideNav(): JSX.Element` — `<nav aria-label="Main">`, `hidden md:flex`, fixed left, `bg-surface-strong`, collapsed width 64px; expands to 220px showing labels when `:hover` or `:focus-within` (state in `data-expanded` attribute driven by `onMouseEnter/Leave` + `onFocus/onBlur` capturing; `Escape` collapses and blurs). Community logo (existing branding source if present, else letter mark on `bg-sun`) at top. Primary items, divider, More items. Active item: `aria-current="page"`, `bg-accent text-surface-strong`. Collapsed labels stay in DOM (`sr-only` when collapsed) so accessible names always exist.

- [ ] **Step 1:** Tests: every visible item reachable by `getByRole('link', { name })`; on `/app/events` the Calendar link has `aria-current="page"`; non-admin → no `Admin` link; admin → present; `focus` on first link → nav `data-expanded="true"`; `Escape` → `"false"`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(layout): icon side nav that expands on hover and focus`.

---

### Task 9: BottomTabBar + MoreSheet (phone)

**Files:**
- Create: `components/layout/BottomTabBar.tsx`, `components/layout/MoreSheet.tsx`
- Delete: `components/layout/MobileNav.tsx`
- Test: `tests/unit/layout/BottomTabBar.test.tsx`

**Interfaces:**
- Consumes: Task 7 nav model, `Drawer` (Task 5), `useSession` (logout action from existing store/api — reuse what `AvatarMenu.tsx` calls today).
- Produces: `BottomTabBar(): JSX.Element` — `<nav aria-label="Primary">`, `md:hidden`, fixed bottom, floating pill `mx-3 mb-[calc(.75rem+env(safe-area-inset-bottom))] rounded-3xl h-[60px] bg-surface-strong text-muted`; 4 `PRIMARY_NAV` links + "More" button (`Ellipsis` icon, `aria-haspopup="dialog"`, `aria-expanded`). Active: `text-accent`, `aria-current="page"`.
- Produces: `MoreSheet({ open, onClose }: { open: boolean; onClose: () => void })` — `Drawer side="bottom" title="More"`; lists `visibleNav(MORE_NAV, isAdmin)` + "Sign out" button. Selecting a link closes the sheet.
- Produces constant `TAB_BAR_CLEARANCE = 'pb-[calc(84px+env(safe-area-inset-bottom))] md:pb-0'` exported from `BottomTabBar.tsx` for Shell.

- [ ] **Step 1:** Tests: 4 links + More button by role/name; click More → `dialog` named "More" with Galleries…Help; non-admin no Admin; click "Sign out" calls mocked logout; `Escape` closes.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(layout): phone bottom tab bar with more sheet`.

---

### Task 10: TopBar + Shell assembly

**Files:**
- Rewrite: `components/layout/TopBar.tsx`, `components/layout/Shell.tsx`, `components/layout/AvatarMenu.tsx`
- Modify: `app/app/layout.tsx` (drop `PageTransition`)
- Delete: `components/layout/PageTransition.tsx`
- Test: `tests/unit/layout/Shell.test.tsx`, `tests/unit/layout/TopBar.test.tsx`

**Interfaces:**
- Consumes: `SideNav`, `BottomTabBar`, `TAB_BAR_CLEARANCE`, `TooltipProvider`, `ToastRoot`, existing `NotificationsBell`, `GlobalCommandPalette`, `FloatingChatDock`, `useUI().setCommandPaletteOpen`.
- `TopBar()`: phone (< md): sticky, `bg-bg`, logo mark left; right: search `IconButton aria-label="Search"` (opens palette) + `NotificationsBell`. Desktop (≥ md): no logo (side nav has it); right-aligned search + bell + `AvatarMenu`. `AvatarMenu` restyled with shadcn `dropdown-menu` (`npx shadcn@latest add dropdown-menu`), same items as today.
- `Shell({ children })`: keep existing auth-gating/session logic verbatim; layout = `SideNav` + column (`md:pl-16`) containing `TopBar` + `<main id="main" className={cn('px-4 md:px-8', TAB_BAR_CLEARANCE)}>` + `BottomTabBar`. `FloatingChatDock` wrapped in `<div className="hidden md:block">`. Add skip link "Skip to content" → `#main` as first focusable element. Wrap in `TooltipProvider`. Mount `ToastRoot`, `GlobalCommandPalette`, `ModalRoot`.
- Leave `PageMasthead.tsx`, `GroupContextSwitcher.tsx` untouched (re-skinned in their area phases); remove them from Shell if Shell currently renders them, otherwise ignore.

- [ ] **Step 1:** Tests (mock session as authenticated):
  - Shell: renders `navigation` "Main" and "Primary"; `main` has class containing `env(safe-area-inset-bottom)`; first Tab focuses link "Skip to content"; chat dock wrapper has `hidden md:block`.
  - TopBar: clicking "Search" calls `setCommandPaletteOpen(true)`; bell rendered.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(layout): garden club shell with top bar and skip link`.

---

### Task 11: Phase gate + docs

**Files:**
- Modify: root `CLAUDE.md` (Frontend section), `plans/project_plan.md` (Nuxt mentions)
- Modify: `docs/superpowers/plans/2026-10-20-frontend-overhaul-index.md` (mark P1 done)

- [ ] **Step 1:** `npx vitest run tests/unit/ui tests/unit/layout tests/unit/theme tests/unit/lib tests/unit/app/providers.test.tsx` → all PASS.
- [ ] **Step 2:** `npx eslint components/ui components/layout theme lib app/layout.tsx app/providers.tsx app/globals.css` → 0 errors. `npx prettier --check` same paths → clean.
- [ ] **Step 3:** `grep -rn "@mui\|@emotion\|@heroicons" components/ui components/layout app/layout.tsx app/providers.tsx theme lib` → no output.
- [ ] **Step 4:** Manual check (`npm run dev`, `/app` at 390px and 1280px widths, light + dark): tab bar floats above iPhone safe area, side nav expands on hover and Tab, focus ring visible, no theme flash on reload. Note: pages themselves may error (still Joy) — only the shell is judged.
- [ ] **Step 5:** Replace `CLAUDE.md` "### Frontend" body with: `Next.js 16 App Router, React 19, Tailwind v4 + shadcn/ui (Radix) in components/ui, Lucide icons, TanStack Query (lib/api, hooks), zustand (stores), next-intl, next-themes (class). Tokens: app/globals.css + theme/palette.ts (AA test in tests/unit/theme). Shell: components/layout/{Shell,SideNav,BottomTabBar,MoreSheet,TopBar}.` Fix Nuxt references in `plans/project_plan.md` and the CLAUDE.md Project line.
- [ ] **Step 6:** Commit `docs: update frontend stack notes for tailwind/shadcn`; merge `feat/fo-p1-foundation-shell` → `feat/frontend-overhaul`.
