/**
 * @file components/galleries/galleries-page/SectionLabel.tsx
 * @brief Section heading with an optional right-aligned kicker.
 */

/**
 * @brief Heading row with bottom rule.
 * @param label heading text
 * @param kicker optional muted text at the right
 * @return header element
 */
export function SectionLabel({
  label,
  kicker,
}: {
  label: string;
  kicker?: string;
}) {
  return (
    <div className="border-ink/15 flex items-baseline gap-3 border-b pb-3">
      <h2 className="text-2xl font-black tracking-tight md:text-3xl">
        {label}
      </h2>
      {kicker && <span className="text-muted ml-auto text-sm">{kicker}</span>}
    </div>
  );
}
