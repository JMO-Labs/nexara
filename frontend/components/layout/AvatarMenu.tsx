'use client';
/**
 * @file components/layout/AvatarMenu.tsx
 * @brief Avatar dropdown with profile / settings / sign-out.
 */
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Menu from '@mui/joy/Menu';
import MenuItem from '@mui/joy/MenuItem';
import MenuButton from '@mui/joy/MenuButton';
import Dropdown from '@mui/joy/Dropdown';
import ListDivider from '@mui/joy/ListDivider';
import { Avatar } from '@/components/ui/Avatar';
import { useSession } from '@/stores/session';
import { useModals } from '@/stores/modals';
import { logout as apiLogout } from '@/lib/api/auth';
import { setAccessToken } from '@/lib/auth/session';

export function AvatarMenu() {
  const router = useRouter();
  const user = useSession((s) => s.user);
  const reset = useSession((s) => s.reset);
  const setKeyboardShortcutsOpen = useModals((s) => s.setKeyboardShortcutsOpen);

  const onLogout = async () => {
    try {
      await apiLogout();
    } catch {
      /* ignore — local state is what matters */
    }
    setAccessToken(null);
    reset();
    router.replace('/login');
  };

  return (
    <Dropdown>
      <MenuButton
        slots={{ root: 'button' }}
        slotProps={{
          root: {
            'aria-label': 'Account menu',
            'aria-haspopup': 'menu',
            style: { background: 'transparent', border: 0, padding: 4, cursor: 'pointer' },
          },
        }}
      >
        <Avatar
          src={user?.avatar_url ?? undefined}
          alt={user?.display_name ?? 'You'}
          size="sm"
        >
          {user?.display_name?.[0] ?? '?'}
        </Avatar>
      </MenuButton>
      <Menu placement="bottom-end" sx={{ minWidth: 220 }}>
        <MenuItem disabled sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
          <span style={{ fontWeight: 600 }}>{user?.display_name ?? 'Signed in'}</span>
          <span style={{ fontSize: '0.78rem', opacity: 0.7 }}>{user?.email}</span>
        </MenuItem>
        <ListDivider />
        <MenuItem component={Link} href="/app/settings">
          Settings
        </MenuItem>
        <MenuItem component={Link} href="/app/admin">
          Admin
        </MenuItem>
        <ListDivider />
        <MenuItem onClick={() => setKeyboardShortcutsOpen(true)}>
          Keyboard shortcuts
        </MenuItem>
        <ListDivider />
        <MenuItem color="danger" onClick={onLogout}>
          Sign out
        </MenuItem>
      </Menu>
    </Dropdown>
  );
}
