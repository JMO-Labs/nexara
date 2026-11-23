/**
 * @file components/chat/details/DetailsSection.tsx
 * @brief Titled block inside the details panel. Renders nothing when empty.
 */
import * as React from "react";

export interface DetailsSectionProps {
  title: string;
  /** False hides the whole section (empty data). */
  show?: boolean;
  children: React.ReactNode;
}

/**
 * @param props see DetailsSectionProps
 * @return labelled section or null
 */
export function DetailsSection({
  title,
  show = true,
  children,
}: DetailsSectionProps) {
  const id = React.useId();
  if (!show) return null;
  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <h3 id={id} className="text-sm font-semibold">
        {title}
      </h3>
      {children}
    </section>
  );
}
