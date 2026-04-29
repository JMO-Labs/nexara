"use client";
/**
 * @file components/home/widgets/MediaCarouselWidget.tsx
 * @brief Media carousel widget — fetches aggregated home media and renders
 *        the Carousel primitive. Scope controls let the user filter by
 *        community / a specific subgroup / personal.
 */
import * as React from "react";
import Link from "next/link";
import Stack from "@mui/joy/Stack";
import Box from "@mui/joy/Box";
import { useHomeMedia, type HomeMediaScope } from "@/hooks/useHomeMedia";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { Carousel } from "@/components/ui/Carousel";
import { EmptyState, Skeleton } from "@/components/ui";
import type { Subgroup } from "@/lib/api/subgroups";
import type { WidgetContext } from "@/lib/widgets/registry";

type Scope =
  | { kind: "all" }
  | { kind: "community" }
  | { kind: "personal" }
  | { kind: "subgroup"; subgroupId: string };

const SCOPE_LABELS: Record<HomeMediaScope, string> = {
  all: "All",
  community: "Community",
  subgroup: "Group",
  personal: "Mine",
};

function ScopePill({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <Box
      component="button"
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className="rgl-cancel"
      sx={{
        all: "unset",
        cursor: "pointer",
        px: 1.25,
        py: 0.4,
        borderRadius: "sm",
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: "0.02em",
        border: "1px solid",
        borderColor: active ? "primary.500" : "divider",
        bgcolor: active ? "primary.softBg" : "transparent",
        color: active ? "primary.plainColor" : "text.secondary",
        transition: "all 120ms",
        "&:hover": { borderColor: active ? "primary.500" : "neutral.300" },
      }}
    >
      {label}
    </Box>
  );
}

export function MediaCarouselWidget(_: WidgetContext) {
  const [scope, setScope] = React.useState<Scope>({ kind: "all" });
  const { data: subgroupsData } = useSubgroupList();
  const subgroups = ((subgroupsData as Subgroup[] | undefined) ?? []).filter(
    (sg) => sg.my_role !== null,
  );

  const params = React.useMemo(() => {
    if (scope.kind === "subgroup") {
      return { limit: 24, scope: "subgroup" as const, subgroupId: scope.subgroupId };
    }
    return { limit: 24, scope: scope.kind };
  }, [scope]);

  const { data, isLoading } = useHomeMedia(params);

  const items = data?.items ?? [];

  return (
    <Stack spacing={1.25}>
      <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap" }}>
        <ScopePill
          active={scope.kind === "all"}
          label={SCOPE_LABELS.all}
          onClick={() => setScope({ kind: "all" })}
        />
        <ScopePill
          active={scope.kind === "community"}
          label={SCOPE_LABELS.community}
          onClick={() => setScope({ kind: "community" })}
        />
        <ScopePill
          active={scope.kind === "personal"}
          label={SCOPE_LABELS.personal}
          onClick={() => setScope({ kind: "personal" })}
        />
        {subgroups.slice(0, 4).map((sg) => (
          <ScopePill
            key={sg.id}
            active={scope.kind === "subgroup" && scope.subgroupId === sg.id}
            label={sg.name}
            onClick={() => setScope({ kind: "subgroup", subgroupId: sg.id })}
          />
        ))}
      </Stack>

      {isLoading ? (
        <Skeleton height={220} rounded="md" />
      ) : items.length === 0 ? (
        <EmptyState
          title="No media yet"
          description="Media from this scope will appear here."
        />
      ) : (
        <Carousel
          slides={items.map((item) => {
            const isImage = item.media.content_type.startsWith("image/");
            const href =
              item.source === "post"
                ? `/app/post/${item.source_id}`
                : `/app/galleries/${item.source_id}`;
            return (
              <Link
                key={item.media_id}
                href={href}
                aria-label={item.source_title ?? "Media item"}
                className="block relative w-full overflow-hidden rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)]"
                style={{ aspectRatio: "16/9" }}
              >
                {isImage ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={item.media.thumbnail_key ?? item.media.storage_key}
                    alt={item.media.alt_text ?? item.source_title ?? ""}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-neutral-100 dark:bg-neutral-800">
                    <span className="text-neutral-500 text-sm">
                      {item.source_title ?? "Media"}
                    </span>
                  </div>
                )}
                {item.source_title && (
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-3 py-2">
                    <p className="text-white text-xs font-medium truncate">
                      {item.source_title}
                    </p>
                  </div>
                )}
              </Link>
            );
          })}
          slidesPerView={3}
          loop
          ariaLabel="Media from your groups"
          showArrows
          showDots
        />
      )}
    </Stack>
  );
}

export default MediaCarouselWidget;
