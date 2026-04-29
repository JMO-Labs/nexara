/**
 * @file stores/confirmDialog.ts
 * @brief Global confirm dialog store. Provides an imperative async API:
 *        `await confirm({ title, message, tone })` returns true on confirm,
 *        false on cancel or Escape.
 */
import { create } from 'zustand';

export type ConfirmTone = 'neutral' | 'danger';

export interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: ConfirmTone;
}

interface ConfirmDialogState {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  tone: ConfirmTone;
  /** Internal resolver — set when confirm() is called. */
  _resolve: ((value: boolean) => void) | null;
  /** Imperative trigger; returns promise that resolves on user action. */
  confirm: (opts: ConfirmOptions) => Promise<boolean>;
  /** Resolve false and close. */
  close: () => void;
  /** Resolve true and close. */
  accept: () => void;
}

export const useConfirmDialog = create<ConfirmDialogState>((set, get) => ({
  isOpen: false,
  title: '',
  message: '',
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  tone: 'neutral',
  _resolve: null,

  confirm: (opts) => {
    // Reject any pending dialog first
    get()._resolve?.(false);
    return new Promise<boolean>((resolve) => {
      set({
        isOpen: true,
        title: opts.title,
        message: opts.message,
        confirmLabel: opts.confirmLabel ?? 'Confirm',
        cancelLabel: opts.cancelLabel ?? 'Cancel',
        tone: opts.tone ?? 'neutral',
        _resolve: resolve,
      });
    });
  },

  close: () => {
    get()._resolve?.(false);
    set({ isOpen: false, _resolve: null });
  },

  accept: () => {
    get()._resolve?.(true);
    set({ isOpen: false, _resolve: null });
  },
}));
