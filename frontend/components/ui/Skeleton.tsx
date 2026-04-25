'use client';
/**
 * @file components/ui/Skeleton.tsx
 * @brief Editorial skeleton — fog shimmer over paper. Animated via CSS
 *        keyframes for cheap repeated use; reduced-motion disables.
 *        Mount/unmount wrapped in motion.div for fade effect.
 */
import * as React from 'react';
import Box, { type BoxProps } from '@mui/joy/Box';
import { motion } from 'framer-motion';

export type SkeletonProps = BoxProps & {
  width?: number | string;
  height?: number | string;
  rounded?: 'sm' | 'md' | 'lg' | 'pill';
};

const rad = { sm: 'sm', md: 'md', lg: 'lg', pill: '999px' } as const;

export function Skeleton({ width = '100%', height = 16, rounded = 'sm', sx, ...rest }: SkeletonProps) {
  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.2 } }}
    >
      <Box
        role="status"
        aria-busy="true"
        aria-live="polite"
        sx={{
          width,
          height,
          borderRadius: rad[rounded],
          background: 'linear-gradient(90deg, var(--nx-palette-neutral-100) 0%, var(--nx-palette-neutral-200) 50%, var(--nx-palette-neutral-100) 100%)',
          backgroundSize: '200% 100%',
          animation: 'nx-shimmer 1400ms ease-in-out infinite',
          '@keyframes nx-shimmer': {
            '0%': { backgroundPosition: '200% 0' },
            '100%': { backgroundPosition: '-200% 0' },
          },
          '@media (prefers-reduced-motion: reduce)': {
            animation: 'none',
          },
          ...sx,
        }}
        {...rest}
      />
    </motion.div>
  );
}

export default Skeleton;
