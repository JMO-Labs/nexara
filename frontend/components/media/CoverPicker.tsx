"use client";
/**
 * @file components/media/CoverPicker.tsx
 * @brief Cover/banner image control: upload a file or paste an image link
 *        (imported server-side), with preview and remove. Emits a media id.
 */
import * as React from "react";
import { Link2 } from "lucide-react";
import { Button } from "@/components/ui";
import { MediaThumb } from "@/components/galleries/MediaThumb";
import { useMediaUpload } from "@/hooks/useMediaUpload";
import { importMediaUrl } from "@/lib/api/media";

export interface CoverPickerProps {
  mediaId: string | null;
  /** Selected cover is NSFW (blurred with a badge). */
  nsfw?: boolean;
  onChange: (mediaId: string | null) => void;
  label?: string;
}

/**
 * @brief Cover picker.
 * @param props current media id, change handler, label
 * @return field element
 */
export function CoverPicker({
  mediaId,
  nsfw,
  onChange,
  label = "Cover image",
}: CoverPickerProps) {
  const upload = useMediaUpload();
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [linkOpen, setLinkOpen] = React.useState(false);
  const [url, setUrl] = React.useState("");
  const [importing, setImporting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const busy = upload.isPending || importing;

  const pickFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setError(null);
    try {
      onChange(await upload.mutateAsync(file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    }
  };

  const importLink = async () => {
    const link = url.trim();
    if (!/^https?:\/\/\S+$/i.test(link)) {
      setError("Paste a full image link starting with http:// or https://");
      return;
    }
    setError(null);
    setImporting(true);
    try {
      onChange((await importMediaUrl(link)).id);
      setUrl("");
      setLinkOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't use that link.");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-semibold">{label}</span>
      {mediaId && (
        <div className="relative h-36 w-full overflow-hidden rounded-2xl bg-surface">
          <MediaThumb mediaId={mediaId} alt={`${label} preview`} nsfw={nsfw} />
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="secondary"
          loading={upload.isPending}
          disabled={busy}
          onClick={() => fileRef.current?.click()}
        >
          Upload image
        </Button>
        <Button
          type="button"
          variant="ghost"
          disabled={busy}
          aria-expanded={linkOpen}
          onClick={() => setLinkOpen((v) => !v)}
        >
          <Link2 className="size-4" aria-hidden /> Use a link
        </Button>
        {mediaId && (
          <Button
            type="button"
            variant="ghost"
            disabled={busy}
            onClick={() => onChange(null)}
          >
            Remove
          </Button>
        )}
      </div>
      {linkOpen && (
        <div className="flex gap-2">
          <input
            type="url"
            aria-label="Image link"
            placeholder="https://example.com/photo.jpg"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void importLink();
              }
            }}
            className="min-w-0 flex-1 rounded-full bg-[color-mix(in_srgb,var(--nx-ink)_6%,transparent)] px-4 py-2 text-sm outline-none focus-visible:outline-2 focus-visible:outline-accent"
          />
          <Button
            type="button"
            loading={importing}
            onClick={() => void importLink()}
          >
            Add
          </Button>
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        hidden
        aria-label={`${label} file`}
        onChange={pickFile}
      />
    </div>
  );
}
