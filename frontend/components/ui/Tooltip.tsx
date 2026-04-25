'use client';
/**
 * @file components/ui/Tooltip.tsx
 * @brief Tooltip primitive with optional shortcut badge display.
 */
import { Tooltip as JoyTooltip, type TooltipProps } from '@mui/joy';
import { Box } from '@mui/joy';
import type { ReactNode } from 'react';

export interface AppTooltipProps extends Omit<TooltipProps, 'title' | 'children'> {
  title: ReactNode;
  shortcut?: string;
  children: ReactNode;
  disabled?: boolean;
}

export function Tooltip({
  title,
  shortcut,
  children,
  disabled,
  placement = 'top',
  ...rest
}: AppTooltipProps) {
  if (disabled) return <>{children}</>;
  const body = shortcut ? (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <span>{title}</span>
      <Box
        component="kbd"
        sx={{
          px: 0.5,
          py: 0.125,
          borderRadius: 4,
          fontSize: 11,
          bgcolor: 'neutral.softBg',
          color: 'neutral.softColor',
          fontFamily: 'monospace',
        }}
      >
        {shortcut}
      </Box>
    </Box>
  ) : (
    title
  );
  return (
    <JoyTooltip
      title={body}
      placement={placement}
      enterDelay={400}
      leaveDelay={0}
      arrow
      variant="outlined"
      {...rest}
    >
      <span style={{ display: 'inline-flex' }}>{children}</span>
    </JoyTooltip>
  );
}

export default Tooltip;
