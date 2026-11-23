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

/**
 * @brief Photo grid shared by both detail kinds.
 * @param media thumbnails (links open the media viewer)
 */
export function PhotoGrid({
  media,
}: {
  media: { id: string; thumb_url: string }[];
}) {
  return (
    <DetailsSection title="Shared photos" show={media.length > 0}>
      <ul className="grid list-none grid-cols-3 gap-1.5 p-0">
        {media.map((m) => (
          <li key={m.id}>
            <a
              href={`/app/media/${m.id}`}
              aria-label="Open photo"
              className="block aspect-square overflow-hidden rounded-xl outline-none focus-visible:outline-2 focus-visible:outline-accent"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={m.thumb_url}
                alt=""
                className="size-full object-cover"
              />
            </a>
          </li>
        ))}
      </ul>
    </DetailsSection>
  );
}
