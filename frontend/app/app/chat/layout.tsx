/**
 * @file app/app/chat/layout.tsx
 * @brief Strips the Shell main padding for chat. Chat pane fills the
 *        viewport's main area exactly; composer cannot be scrolled past.
 */
import type { ReactNode } from 'react';
import Box from '@mui/joy/Box';

export default function ChatLayout({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        flex: 1,
        minHeight: 0,
        display: 'flex',
        mx: { xs: -2, md: -3 },
        my: { xs: -2, md: -3 },
      }}
    >
      {children}
    </Box>
  );
}
