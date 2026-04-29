'use client';
/**
 * @file components/ui/ConfirmDialog.tsx
 * @brief Global confirm dialog backed by useConfirmDialog store.
 *        Mount once in Shell. Use `await confirm({ ... })` imperative API.
 * @return boolean — true if user confirmed, false if cancelled or Escaped.
 */
import * as React from 'react';
import JoyModal from '@mui/joy/Modal';
import ModalDialog from '@mui/joy/ModalDialog';
import Typography from '@mui/joy/Typography';
import Stack from '@mui/joy/Stack';
import { Button } from '@/components/ui/Button';
import { useConfirmDialog } from '@/stores/confirmDialog';

export function ConfirmDialog() {
  const isOpen = useConfirmDialog((s) => s.isOpen);
  const title = useConfirmDialog((s) => s.title);
  const message = useConfirmDialog((s) => s.message);
  const confirmLabel = useConfirmDialog((s) => s.confirmLabel);
  const cancelLabel = useConfirmDialog((s) => s.cancelLabel);
  const tone = useConfirmDialog((s) => s.tone);
  const close = useConfirmDialog((s) => s.close);
  const accept = useConfirmDialog((s) => s.accept);

  return (
    <JoyModal
      open={isOpen}
      onClose={close}
      aria-labelledby="confirm-dialog-title"
    >
      <ModalDialog
        size="sm"
        sx={{
          borderRadius: 'lg',
          maxWidth: 400,
          width: 'calc(100vw - 32px)',
        }}
      >
        <Typography
          id="confirm-dialog-title"
          level="h4"
          sx={{ fontFamily: 'var(--font-display)' }}
        >
          {title}
        </Typography>
        <Typography level="body-md" textColor="text.secondary">
          {message}
        </Typography>
        <Stack direction="row" spacing={1} justifyContent="flex-end" sx={{ mt: 1 }}>
          <Button
            variant="outlined"
            color="neutral"
            onClick={close}
            data-testid="confirm-dialog-cancel"
          >
            {cancelLabel}
          </Button>
          <Button
            variant="solid"
            color={tone === 'danger' ? 'danger' : 'primary'}
            onClick={accept}
            data-testid="confirm-dialog-confirm"
          >
            {confirmLabel}
          </Button>
        </Stack>
      </ModalDialog>
    </JoyModal>
  );
}

export default ConfirmDialog;
