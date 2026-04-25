'use client';
/**
 * @file components/ui/Modal.tsx
 * @brief Joy Modal + ModalDialog with framer-motion entrance on the
 *        inner content. Backdrop fade handled by Joy.
 */
import * as React from 'react';
import JoyModal from '@mui/joy/Modal';
import ModalDialog, { type ModalDialogProps } from '@mui/joy/ModalDialog';
import ModalClose from '@mui/joy/ModalClose';
import Typography from '@mui/joy/Typography';
import { motion } from 'framer-motion';
import { modalVariants } from './motion';

export interface ModalProps extends Omit<ModalDialogProps, 'title'> {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  hideClose?: boolean;
  children: React.ReactNode;
}

export function Modal({
  open,
  onClose,
  title,
  hideClose,
  children,
  sx,
  size = 'md',
  ...rest
}: ModalProps) {
  return (
    <JoyModal open={open} onClose={onClose}>
      <ModalDialog
        size={size}
        sx={{
          borderRadius: 'lg',
          maxWidth: 560,
          width: 'calc(100vw - 32px)',
          ...sx,
        }}
        {...rest}
      >
        <motion.div
          variants={modalVariants}
          initial="hidden"
          animate="show"
          style={{ display: 'contents' }}
        >
          {!hideClose && <ModalClose />}
          {title && (
            <Typography level="h3" sx={{ fontFamily: 'var(--font-display)' }}>
              {title}
            </Typography>
          )}
          {children}
        </motion.div>
      </ModalDialog>
    </JoyModal>
  );
}

export default Modal;
