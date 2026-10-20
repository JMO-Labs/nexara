"use client";
/**
 * @file components/subgroups/create-subgroup/CoverField.tsx
 * @brief Optional cover image upload / preview / remove control.
 */
import * as React from "react";
import { Button } from "@/components/ui";
import { MediaThumb } from "@/components/galleries/MediaThumb";

export interface CoverFieldProps {
  mediaId: string | null;
  uploading: boolean;
  onUpload: (file: File) => void;
  onRemove: () => void;
}

/**
 * @brief Cover image field.
 * @param props current media id and handlers
 * @return field element
 */
export function CoverField({
  mediaId,
  uploading,
  onUpload,
  onRemove,
}: CoverFieldProps) {
  const fileRef = React.useRef<HTMLInputElement>(null);
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm font-semibold">Cover image (optional)</span>
      {mediaId ? (
        <div className="relative h-20 w-[100px] overflow-hidden rounded-xl border border-current/20">
          <MediaThumb mediaId={mediaId} alt="Cover preview" />
          <Button
            type="button"
            size="sm"
            variant="destructive"
            onClick={onRemove}
            className="absolute right-1 bottom-1 h-7 px-2 text-xs"
          >
            Remove
          </Button>
        </div>
      ) : (
        <div>
          <Button
            type="button"
            variant="secondary"
            className="min-h-11"
            loading={uploading}
            onClick={() => fileRef.current?.click()}
          >
            Upload cover
          </Button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onUpload(f);
            }}
          />
        </div>
      )}
    </div>
  );
}

export default CoverField;
