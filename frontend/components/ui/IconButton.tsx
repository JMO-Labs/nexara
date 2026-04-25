'use client';
/**
 * @file components/ui/IconButton.tsx
 * @brief Joy IconButton wrapped with motion.span for press feedback and optional tooltip.
 */
import * as React from 'react';
import JoyIconButton, { type IconButtonProps as JoyIconButtonProps } from '@mui/joy/IconButton';
import { motion } from 'framer-motion';
import { spring } from './motion';
import { Tooltip } from './Tooltip';

export interface IconButtonProps extends Omit<JoyIconButtonProps, 'tooltip'> {
  tooltip?: string;
  shortcut?: string;
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton({ tooltip, shortcut, ...props }, ref) {
    const button = (
      <motion.span whileTap={{ scale: 0.92 }} transition={spring} style={{ display: 'inline-flex' }}>
        <JoyIconButton ref={ref} {...props} />
      </motion.span>
    );

    if (tooltip) {
      return (
        <Tooltip title={tooltip} shortcut={shortcut}>
          {button}
        </Tooltip>
      );
    }

    return button;
  },
);

export default IconButton;
