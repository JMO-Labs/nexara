'use client';
/**
 * @file components/ui/Avatar.tsx
 * @brief Avatar with optional terracotta active ring. Re-exports Joy
 *        AvatarGroup for stack patterns.
 */
import * as React from 'react';
import JoyAvatar, { type AvatarProps as JoyAvatarProps } from '@mui/joy/Avatar';
import AvatarGroup from '@mui/joy/AvatarGroup';

export type AvatarProps = JoyAvatarProps & {
  active?: boolean;
};

export const Avatar = React.forwardRef<HTMLDivElement, AvatarProps>(function Avatar(
  { active, sx, ...rest },
  ref,
) {
  return (
    <JoyAvatar
      ref={ref as never}
      sx={{
        ...(active && {
          boxShadow: '0 0 0 2px var(--nx-palette-background-surface), 0 0 0 4px var(--nx-palette-primary-500)',
        }),
        ...sx,
      }}
      {...rest}
    />
  );
});

export { AvatarGroup };
export default Avatar;
