'use client';
/**
 * @file components/ui/Toast.tsx
 * @brief ToastRoot — subscribes to useToasts store, renders an ARIA live
 *        region of stacked toasts. Auto-dismisses after ttl.
 */
import * as React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Box from '@mui/joy/Box';
import Alert from '@mui/joy/Alert';
import IconButton from '@mui/joy/IconButton';
import Typography from '@mui/joy/Typography';
import { useToasts, type Toast as ToastT, type ToastVariant } from '@/stores/toasts';
import { spring } from './motion';

const variantColor: Record<ToastVariant, 'primary' | 'success' | 'warning' | 'danger' | 'neutral'> = {
  info: 'neutral',
  success: 'success',
  warning: 'warning',
  danger: 'danger',
  loading: 'primary',
};

function ToastItem({ toast }: { toast: ToastT }) {
  const dismiss = useToasts((s) => s.dismiss);
  React.useEffect(() => {
    if (!toast.ttl) return;
    const t = setTimeout(() => dismiss(toast.id), toast.ttl);
    return () => clearTimeout(t);
  }, [toast.id, toast.ttl, dismiss]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 24, scale: 0.96 }}
      animate={{ opacity: 1, x: 0, scale: 1, transition: spring }}
      exit={{ opacity: 0, x: 24, scale: 0.98, transition: { duration: 0.18 } }}
    >
      <Alert
        color={variantColor[toast.variant]}
        variant="soft"
        sx={{ borderRadius: 'md', minWidth: 280, maxWidth: 420, boxShadow: 'md', alignItems: 'flex-start' }}
        endDecorator={
          <IconButton
            size="sm"
            variant="plain"
            color={variantColor[toast.variant]}
            onClick={() => dismiss(toast.id)}
            aria-label="Dismiss notification"
          >
            ✕
          </IconButton>
        }
      >
        <Box>
          {toast.title && (
            <Typography level="title-sm" sx={{ fontFamily: 'var(--font-display)' }}>
              {toast.title}
            </Typography>
          )}
          <Typography level="body-sm">{toast.message}</Typography>
        </Box>
      </Alert>
    </motion.div>
  );
}

export function ToastRoot() {
  const items = useToasts((s) => s.items).slice(0, 3);
  return (
    <Box
      role="region"
      aria-live="polite"
      aria-label="Notifications"
      sx={{
        position: 'fixed',
        bottom: 16,
        right: 16,
        zIndex: 1500,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        pointerEvents: 'none',
        '& > *': { pointerEvents: 'auto' },
      }}
    >
      <AnimatePresence initial={false}>
        {items.map((t) => (
          <ToastItem key={t.id} toast={t} />
        ))}
      </AnimatePresence>
    </Box>
  );
}

export default ToastRoot;
