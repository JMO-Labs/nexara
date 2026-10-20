"use client";
/**
 * @file components/layout/MoreSheet.tsx
 * @brief Bottom sheet listing overflow nav items and sign out (phone).
 */
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { Drawer } from "@/components/ui/Drawer";
import { useSession } from "@/stores/session";
import { logout as apiLogout } from "@/lib/api/auth";
import { setAccessToken } from "@/lib/auth/session";
import { MORE_NAV, visibleNav } from "./navItems";

const ROW =
  "flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-ink hover:bg-surface-strong";

/**
 * @brief More sheet.
 * @param props open state and close handler
 * @return drawer element
 */
export function MoreSheet({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const isAdmin = useSession((s) => !!s.user?.is_admin);
  const reset = useSession((s) => s.reset);

  const onLogout = async () => {
    try {
      await apiLogout();
    } catch {
      /* local state is what matters */
    }
    setAccessToken(null);
    reset();
    onClose();
    router.replace("/login");
  };

  return (
    <Drawer open={open} onClose={onClose} title="More" side="bottom">
      <ul className="m-0 list-none p-0">
        {visibleNav(MORE_NAV, isAdmin).map(({ label, href, Icon }) => (
          <li key={href}>
            <Link href={href} onClick={onClose} className={ROW}>
              <Icon aria-hidden className="size-5" />
              <span>{label}</span>
            </Link>
          </li>
        ))}
        <li>
          <button type="button" onClick={onLogout} className={ROW}>
            <LogOut aria-hidden className="size-5" />
            <span>Sign out</span>
          </button>
        </li>
      </ul>
    </Drawer>
  );
}
