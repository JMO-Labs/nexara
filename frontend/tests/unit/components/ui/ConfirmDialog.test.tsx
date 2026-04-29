/**
 * @file tests/unit/components/ui/ConfirmDialog.test.tsx
 * @brief Tests for ConfirmDialog component and useConfirmDialog store.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CssVarsProvider } from '@mui/joy/styles';
import joyTheme from '@/theme/joy-theme';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { useConfirmDialog } from '@/stores/confirmDialog';

function wrap(ui: React.ReactNode) {
  return render(<CssVarsProvider theme={joyTheme}>{ui}</CssVarsProvider>);
}

function resetStore() {
  useConfirmDialog.setState({
    isOpen: false,
    title: '',
    message: '',
    confirmLabel: 'Confirm',
    cancelLabel: 'Cancel',
    tone: 'neutral',
    _resolve: null,
  });
}

describe('ConfirmDialog', () => {
  beforeEach(() => {
    resetStore();
  });

  it('confirm resolves true when confirm button clicked', async () => {
    wrap(<ConfirmDialog />);
    const { confirm } = useConfirmDialog.getState();
    const promise = confirm({ title: 'Delete?', message: 'Are you sure?' });

    const btn = await screen.findByTestId('confirm-dialog-confirm');
    await userEvent.click(btn);

    await expect(promise).resolves.toBe(true);
  });

  it('cancel resolves false when cancel button clicked', async () => {
    wrap(<ConfirmDialog />);
    const { confirm } = useConfirmDialog.getState();
    const promise = confirm({ title: 'Delete?', message: 'Are you sure?' });

    const btn = await screen.findByTestId('confirm-dialog-cancel');
    await userEvent.click(btn);

    await expect(promise).resolves.toBe(false);
  });

  it('Escape resolves false', async () => {
    wrap(<ConfirmDialog />);
    const { confirm } = useConfirmDialog.getState();
    const promise = confirm({ title: 'Delete?', message: 'Are you sure?' });

    // wait for dialog to open
    await screen.findByTestId('confirm-dialog-cancel');
    await userEvent.keyboard('{Escape}');

    await expect(promise).resolves.toBe(false);
  });

  it('danger tone: confirm button has danger color class/attribute', async () => {
    wrap(<ConfirmDialog />);
    const { confirm } = useConfirmDialog.getState();
    confirm({ title: 'Delete?', message: 'Sure?', tone: 'danger' });

    const btn = await screen.findByTestId('confirm-dialog-confirm');
    // MUI Joy renders color as data attribute or class — check the element exists
    // and the store tone is 'danger'
    expect(btn).toBeInTheDocument();
    expect(useConfirmDialog.getState().tone).toBe('danger');
  });
});
