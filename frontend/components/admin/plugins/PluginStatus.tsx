/**
 * @file components/admin/plugins/PluginStatus.tsx
 * @brief Plugin status badge (icon + text, never colour alone) and plain-language
 *        copy for plugin-host errors.
 */
import {
  AlertTriangle,
  CheckCircle2,
  CircleOff,
  Loader2,
  type LucideIcon,
} from "lucide-react";
import { Badge } from "@/components/ui";
import type { PluginInstall } from "@/lib/api/plugins";

type Tone = "neutral" | "accent" | "sun" | "leaf";

const STATUS: Record<string, { label: string; icon: LucideIcon; tone: Tone }> =
  {
    running: { label: "Running", icon: CheckCircle2, tone: "leaf" },
    installing: { label: "Installing", icon: Loader2, tone: "accent" },
    needs_config: { label: "Starting", icon: Loader2, tone: "accent" },
    stopped: { label: "Stopped", icon: CircleOff, tone: "neutral" },
    disabled: { label: "Stopped", icon: CircleOff, tone: "neutral" },
    failed: { label: "Failed", icon: AlertTriangle, tone: "sun" },
    sandbox_unavailable: {
      label: "Sandbox unavailable",
      icon: AlertTriangle,
      tone: "sun",
    },
    unreachable: {
      label: "Plugin host unreachable",
      icon: AlertTriangle,
      tone: "sun",
    },
  };

const ERRORS: Record<string, string> = {
  sandbox_unavailable:
    "The plugin sandbox cannot start on this server, so no plugins can run. Check the plugin host container's security settings.",
  sha256_mismatch:
    "The downloaded package did not match its checksum. Check the package URL and SHA-256.",
  start_failed:
    "The plugin was installed but would not start. Its log below may say why.",
  install_error: "Installing the plugin's dependencies failed.",
  cleanup_failed:
    "The plugin host could not remove the plugin's files. Try uninstalling again.",
  unreachable:
    "Nexara cannot reach the plugin host right now. It retries every minute.",
};

/**
 * @brief Plain-language explanation of a plugin-host error code.
 * @param code error code from the host (or "unreachable")
 * @return sentence, or a generic fallback naming the code
 */
export function hostErrorText(code: string): string {
  return ERRORS[code] ?? `The plugin host reported a problem (${code}).`;
}

/**
 * @brief Status for display: live host status for package plugins, else the
 *        stored install status.
 * @param p plugin
 * @return status key
 */
export function displayStatus(p: PluginInstall): string {
  return (p.source === "package" && p.host_status) || p.status;
}

/**
 * @brief Status badge with icon and text.
 * @param status status key
 * @return badge
 */
export function PluginStatusBadge({ status }: { status: string }) {
  const s = STATUS[status] ?? {
    label: status,
    icon: CircleOff,
    tone: "neutral" as Tone,
  };
  const Icon = s.icon;
  return (
    <Badge tone={s.tone} className="inline-flex items-center gap-1">
      <Icon aria-hidden="true" className="size-3.5" />
      {s.label}
    </Badge>
  );
}
