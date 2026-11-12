"use client";
/**
 * @file components/settings/StorageTab.tsx
 * @brief Storage quota usage with per-media-type breakdown.
 */
import {
  AlertTriangle,
  AlertCircle,
  FileText,
  Film,
  HardDrive,
  Image,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui";
import { useStorage } from "@/hooks/useStorage";
import { useSession } from "@/stores/session";
import type { StorageUsage } from "@/lib/api/storage";

const GB = 1024 ** 3;
const ROWS: {
  key: keyof StorageUsage["by_type"];
  label: string;
  Icon: LucideIcon;
}[] = [
  { key: "photos", label: "Photos", Icon: Image },
  { key: "videos", label: "Videos", Icon: Film },
  { key: "documents", label: "Documents", Icon: FileText },
  { key: "other", label: "Other", Icon: AlertCircle },
];

/** @brief Format bytes as GB (<=1 decimal) or MB when under 0.1 GB. */
function fmt(bytes: number): string {
  if (bytes > 0 && bytes < GB / 10)
    return `${Math.round(bytes / 1024 ** 2)} MB`;
  return `${Math.round((bytes / GB) * 10) / 10} GB`;
}

/** @brief Bar tone by usage percent: green <70, yellow <90, red otherwise. */
function toneFor(pct: number): "green" | "yellow" | "red" {
  return pct >= 90 ? "red" : pct >= 70 ? "yellow" : "green";
}

const TONE_BG = {
  green: "bg-green-600",
  yellow: "bg-yellow-500",
  red: "bg-red-600",
};

/**
 * @brief Storage tab with usage summary, progress bar, breakdown table.
 * @return storage tab content
 */
export function StorageTab() {
  const userId = useSession((s) => s.user?.id ?? "");
  const { data, isLoading, isError } = useStorage(userId);

  let body: React.ReactNode;
  if (isLoading) body = <p role="status">Loading storage usage…</p>;
  else if (isError || !data)
    body = <p role="alert">Could not load storage usage.</p>;
  else {
    const pct =
      data.quota_bytes > 0 ? (data.used_bytes / data.quota_bytes) * 100 : 0;
    const tone = toneFor(pct);
    const shown = Math.round(pct);
    body = (
      <>
        {pct > 80 && (
          <div
            role="alert"
            className={`mb-4 flex items-start gap-2 rounded-lg border p-3 text-sm ${
              tone === "red"
                ? "border-red-600 text-red-700"
                : "border-yellow-600 text-yellow-800"
            }`}
          >
            <AlertTriangle
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0"
            />
            <span>
              {`You're using ${shown}% of your storage quota. Consider deleting old media.`}
            </span>
          </div>
        )}
        <div
          data-testid="storage-layout"
          className="flex flex-col gap-6 md:flex-row"
        >
          <div className="md:flex-1">
            <p className="mb-2 flex items-center gap-2 font-medium">
              <HardDrive aria-hidden="true" className="size-4" />
              {`${fmt(data.used_bytes)} / ${fmt(data.quota_bytes)} used`}
            </p>
            <div
              role="progressbar"
              aria-label="Storage used"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(Math.min(pct, 100) * 10) / 10}
              aria-valuetext={`${shown}% used`}
              className="h-3 w-full overflow-hidden rounded-full bg-black/10"
            >
              <div
                data-tone={tone}
                className={`h-full ${TONE_BG[tone]}`}
                style={{ width: `${Math.min(pct, 100)}%` }}
              />
            </div>
            <p className="mt-1 text-sm">{shown}% used</p>
            {/* TODO: link to "Manage media" page and bulk delete UI (future). */}
          </div>
          <table className="md:flex-1 text-sm">
            <caption className="sr-only">Storage used by media type</caption>
            <thead>
              <tr>
                <th scope="col" className="text-left">
                  Type
                </th>
                <th scope="col" className="text-right">
                  Size
                </th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map(({ key, label, Icon }) => (
                <tr
                  key={key}
                  tabIndex={0}
                  className="focus-visible:outline focus-visible:outline-2"
                >
                  <th scope="row" className="text-left font-normal">
                    <Icon aria-hidden="true" className="mr-2 inline size-4" />
                    {label}
                  </th>
                  <td className="text-right">{fmt(data.by_type[key])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </>
    );
  }

  return (
    <Card className="max-w-3xl p-4 md:p-6">
      <h2 className="mb-4 text-lg font-semibold">Storage</h2>
      {body}
    </Card>
  );
}
