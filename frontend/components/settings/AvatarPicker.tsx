"use client";
/**
 * @file components/settings/AvatarPicker.tsx
 * @brief Profile photo: upload an image or remove it (back to initials or
 *        Gravatar). Uploaded photos always win over Gravatar.
 */
import * as React from "react";
import { Camera, Trash2 } from "lucide-react";
import { Avatar, Button } from "@/components/ui";
import { useMediaUpload } from "@/hooks/useMediaUpload";
import { useToasts } from "@/stores/toasts";

const GRAVATAR = "https://www.gravatar.com/avatar/";

/** @brief Current photo with upload/remove controls. */
export function AvatarPicker({
  name,
  src,
  onChange,
  disabled,
}: {
  name: string;
  src: string | null | undefined;
  onChange: (mediaId: string | null) => void;
  disabled?: boolean;
}) {
  const upload = useMediaUpload();
  const push = useToasts((s) => s.push);
  const input = React.useRef<HTMLInputElement>(null);
  const uploaded = !!src && !src.startsWith(GRAVATAR);
  const pick = async (file: File | undefined) => {
    if (!file) return;
    if (!file.type.startsWith("image/"))
      return push({ variant: "danger", message: "Choose an image file" });
    try {
      onChange(await upload.mutateAsync(file));
    } catch {
      push({ variant: "danger", message: "Couldn't upload that photo" });
    } finally {
      if (input.current) input.current.value = "";
    }
  };
  const busy = disabled || upload.isPending;
  return (
    <div className="flex items-center gap-4">
      <Avatar
        src={src ?? undefined}
        name={name}
        size="lg"
        className="size-16 text-xl"
      />
      <div className="flex flex-wrap gap-2">
        <input
          ref={input}
          type="file"
          accept="image/*"
          className="sr-only"
          tabIndex={-1}
          aria-hidden
          onChange={(e) => pick(e.target.files?.[0])}
        />
        <Button
          type="button"
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          <Camera className="size-4" aria-hidden />
          {upload.isPending
            ? `Uploading ${upload.progress}%`
            : uploaded
              ? "Change photo"
              : "Upload photo"}
        </Button>
        {uploaded && (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            disabled={busy}
            onClick={() => onChange(null)}
          >
            <Trash2 className="size-4" aria-hidden /> Remove
          </Button>
        )}
      </div>
    </div>
  );
}
