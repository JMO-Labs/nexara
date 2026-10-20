/**
 * @file WelcomeModal.tsx
 * @brief Pre-tour welcome screen with quick action links.
 *
 * Shown before onboarding tour starts for first-time users.
 * Provides direct shortcuts to common first actions.
 */

"use client";

import Link from "next/link";
import { useState } from "react";
import { CalendarDays, CircleUser, Users, type LucideIcon } from "lucide-react";
import { Button, Modal } from "@/components/ui";
import { useSession } from "@/stores/session";
import * as usersApi from "@/lib/api/users";

interface ActionLink {
  icon: LucideIcon;
  label: string;
  href: string;
  description: string;
}

const ACTIONS: ActionLink[] = [
  {
    icon: CircleUser,
    label: "Edit profile",
    href: "/app/settings?tab=profile",
    description: "Complete your profile info",
  },
  {
    icon: Users,
    label: "Find friends",
    href: "/app/members",
    description: "Connect with community members",
  },
  {
    icon: CalendarDays,
    label: "Browse events",
    href: "/app/events",
    description: "Discover upcoming events",
  },
];

export function WelcomeModal() {
  const user = useSession((s) => s.user);
  const setUser = useSession((s) => s.setUser);
  const [isOpen, setIsOpen] = useState(true);

  const shouldShow = !!user && !user.tour_completed_at;

  const markComplete = async () => {
    if (user) setUser({ ...user, tour_completed_at: new Date().toISOString() });
    try {
      await usersApi.completeOnboarding();
    } catch {
      /* ignore */
    }
  };

  const handleSkip = async () => {
    setIsOpen(false);
    await markComplete();
  };

  const handleTakeTour = () => {
    setIsOpen(false);
  };

  const handleClose = async () => {
    setIsOpen(false);
    await markComplete();
  };

  if (!shouldShow) return null;

  return (
    <Modal
      open={isOpen}
      onClose={handleClose}
      title="Welcome to the community!"
      description="Let's help you get started with a quick tour and some useful links."
    >
      <div className="flex flex-col gap-6">
        <ul className="flex flex-col gap-3">
          {ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <li key={action.href}>
                <Link
                  href={action.href}
                  className="hover:bg-surface focus-visible:outline-accent flex items-center gap-3 rounded-xl border border-current/20 p-3 no-underline outline-none transition-colors focus-visible:outline-2"
                >
                  <Icon size={24} aria-hidden="true" className="shrink-0" />
                  <span className="flex flex-col">
                    <span className="text-sm font-semibold">
                      {action.label}
                    </span>
                    <span className="text-muted text-xs">
                      {action.description}
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
        <div className="flex gap-3">
          <Button variant="ghost" className="flex-1" onClick={handleSkip}>
            Skip for now
          </Button>
          <Button className="flex-1" onClick={handleTakeTour}>
            Take tour
          </Button>
        </div>
      </div>
    </Modal>
  );
}
