"use client";
/**
 * @file components/layout/AvatarMenu.tsx
 * @brief Avatar dropdown with settings / admin / shortcuts / sign-out.
 */
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Avatar } from "@/components/ui/Avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/shadcn/dropdown-menu";
import { useSession } from "@/stores/session";
import { useModals } from "@/stores/modals";
import { logout as apiLogout } from "@/lib/api/auth";
import { setAccessToken } from "@/lib/auth/session";

/**
 * @brief Account menu.
 * @return dropdown menu with avatar trigger
 */
export function AvatarMenu() {
  const router = useRouter();
  const user = useSession((s) => s.user);
  const reset = useSession((s) => s.reset);
  const setKeyboardShortcutsOpen = useModals((s) => s.setKeyboardShortcutsOpen);

  const onLogout = async () => {
    try {
      await apiLogout();
    } catch {
      /* ignore: local state is what matters */
    }
    setAccessToken(null);
    reset();
    router.replace("/login");
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account menu"
        className="focus-visible:outline-accent rounded-full p-1 focus-visible:outline-2 focus-visible:outline-offset-2"
      >
        <Avatar
          src={user?.avatar_url ?? undefined}
          name={user?.display_name ?? "You"}
          size="md"
        />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-56">
        <DropdownMenuLabel className="flex flex-col">
          <span className="font-semibold">
            {user?.display_name ?? "Signed in"}
          </span>
          <span className="text-muted text-xs font-normal">{user?.email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/app/settings" data-tour="settings">
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/app/admin" data-tour="admin-link">
            Admin
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => setKeyboardShortcutsOpen(true)}>
          Keyboard shortcuts
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onSelect={onLogout}>
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
