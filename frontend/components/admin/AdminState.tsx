/**
 * @file components/admin/AdminState.tsx
 * @brief Shared loading / notice states and responsive table classes for admin tabs.
 */
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/** @brief Table classes that collapse rows into stacked cards on phone. */
export const stackTable = {
  head: "max-md:sr-only",
  row: "max-md:mb-2 max-md:flex max-md:flex-col max-md:rounded-xl max-md:border max-md:border-ink/10 max-md:p-2",
  cell: "max-md:flex max-md:min-h-11 max-md:items-center max-md:justify-between max-md:gap-3 max-md:before:text-xs max-md:before:font-semibold max-md:before:text-muted max-md:before:content-[attr(data-label)]",
};

/**
 * @brief Centered spinner.
 * @return status element
 */
export function AdminLoading() {
  return (
    <div className="flex items-center justify-center py-16">
      <Loader2
        role="status"
        aria-label="Loading"
        className="size-6 motion-safe:animate-spin"
      />
    </div>
  );
}

/**
 * @brief Inline message box.
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
  return (
    <div
      role="alert"
      className={cn(
        "rounded-2xl border-l-4 bg-surface p-3 text-sm",
        tone === "error" ? "border-danger text-danger" : "border-accent",
      )}
    >
      {children}
    </div>
  );
}
