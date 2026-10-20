/**
 * @file components/auth/AuthCard.tsx
 * @brief Shared brand header + card container for auth form pages.
 */
import type { ReactNode } from "react";
import { Card } from "@/components/ui";

/**
 * @brief Card with community name, title and optional subtitle.
 * @param title heading text
 * @param subtitle optional line under the heading
 * @param children form content
 * @return auth card
 */
export function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-center text-3xl font-black">Nexara</p>
      <Card className="flex flex-col gap-6 p-6">
        <div>
          <h1 className="text-2xl font-semibold">{title}</h1>
          {subtitle && <p className="mt-1 text-sm opacity-80">{subtitle}</p>}
        </div>
        {children}
      </Card>
    </div>
  );
}
