/**
 * @file components/admin/AdminState.tsx
 * @brief Shared loading / notice states and responsive table classes for admin tabs.
 */
import { AlertCircle, Info, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { fadeInOut, useMotionProps } from "@/components/ui/motion";
import { cn } from "@/lib/utils";

/** @brief Table classes that collapse rows into stacked cards on phone. */
export const stackTable = {
  head: "max-md:sr-only",
  row: "max-md:mb-2 max-md:flex max-md:flex-col max-md:glass-item max-md:rounded-[20px] max-md:p-2",
  cell: "max-md:flex max-md:min-h-11 max-md:items-center max-md:justify-between max-md:gap-3 max-md:before:text-xs max-md:before:font-semibold max-md:before:text-muted max-md:before:content-[attr(data-label)]",
};

/**
 * @brief Centered spinner.
 * @return status element
 */
export function AdminLoading() {
  const fade = useMotionProps(fadeInOut);
  return (
    <motion.div
      data-testid="admin-loading"
      className="flex items-center justify-center py-16"
      {...fade}
    >
      <Loader2
        role="status"
        aria-label="Loading"
        className="size-6 motion-safe:animate-spin"
      />
    </motion.div>
  );
}

/**
 * @brief Inline message box: glass row with a tone glyph (no left rail).
 * @param tone error or info
 * @param children message
 * @return alert element
 */
export function AdminNotice({
  tone = "info",
  children,
}: {
  tone?: "error" | "info";
  children: React.ReactNode;
}) {
  const Icon = tone === "error" ? AlertCircle : Info;
  return (
    <div
      role="alert"
      className="glass-item flex items-start gap-2 rounded-[22px] p-3 text-sm text-ink"
    >
      <Icon
        aria-hidden="true"
        className={cn(
          "mt-0.5 size-4 shrink-0",
          tone === "error" ? "text-danger" : "text-accent",
        )}
      />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
