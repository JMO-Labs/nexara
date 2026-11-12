/**
 * @file components/ui/Badge.tsx
 * @brief Badge and removable Chip with Garden Club tones.
 */
import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const tones = {
  neutral: "bg-bg text-ink",
  accent: "bg-accent text-surface-strong",
  sun: "bg-sun text-surface-strong",
  leaf: "bg-leaf text-surface-strong",
} as const;

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: keyof typeof tones;
}

/**
 * @brief Small pill label.
 * @param tone neutral | accent | sun | leaf
 * @return span
 */
export function Badge({ tone = "neutral", className, ...rest }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        tones[tone],
        className,
      )}
      {...rest}
    />
  );
}

export interface ChipProps extends BadgeProps {
  onRemove?: () => void;
}

/**
 * @brief Badge with an optional remove button.
 * @param onRemove when set, renders a button labelled "Remove {children}"
 * @return span
 */
export function Chip({ onRemove, children, ...rest }: ChipProps) {
  return (
    <Badge {...rest}>
      {children}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Remove ${typeof children === "string" ? children : ""}`.trim()}
          className="-mr-1 rounded-full p-0.5 hover:bg-black/10"
        >
          <X className="size-3" aria-hidden="true" />
        </button>
      )}
    </Badge>
  );
}

export default Badge;
