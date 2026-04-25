'use client';
/**
 * @file components/layout/ModalRoot.tsx
 * @brief Single mount point for app-wide overlays: command palette,
 *        imperative modals (driven by useModals), toasts.
 */
import { GlobalCommandPalette } from '@/components/search/GlobalCommandPalette';
import { ToastRoot } from '@/components/ui/Toast';

export function ModalRoot() {
  return (
    <>
      <GlobalCommandPalette />
      <ToastRoot />
    </>
  );
}
