"use client";
/**
 * @file components/home/widgets/MediaCarouselWidget.tsx
 * @brief Media carousel widget — fetches aggregated home media and renders a
 *        rotating slick carousel. Scope pills filter by community / subgroup.
 */
import * as React from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import Stack from "@mui/joy/Stack";
import Box from "@mui/joy/Box";
import "slick-carousel/slick/slick.css";
import "slick-carousel/slick/slick-theme.css";
import { useHomeMedia } from "@/hooks/useHomeMedia";
import { useSubgroupList } from "@/hooks/useSubgroups";
import { EmptyState, Skeleton } from "@/components/ui";
import { API_BASE } from "@/lib/auth/session";
import type { Subgroup } from "@/lib/api/subgroups";
import type { WidgetContext } from "@/lib/widgets/registry";

// react-slick uses `window` at import time; load client-only.
const Slider = dynamic(() => import("react-slick"), { ssr: false });

type Scope =
  | { kind: "all" }
  | { kind: "community" }
  | { kind: "subgroup"; subgroupId: string };

const SCOPE_LABELS: Record<"all" | "community" | "subgroup", string> = {
  all: "All",
  community: "Community",
  subgroup: "Group",
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
  const subgroups = (subgroupsData as Subgroup[] | undefined) ?? [];

  const params = React.useMemo(() => {
    if (scope.kind === "subgroup") {
      return {
        limit: 24,
        scope: "subgroup" as const,
        subgroupId: scope.subgroupId,
      };
    }
    return { limit: 24, scope: scope.kind };
  }, [scope]);

  const { data, isLoading } = useHomeMedia(params);
  const items = data?.items ?? [];

  // Stable slider settings — vanilla slick config per docs
  const sliderSettings = {
    dots: true,
    infinite: items.length > 3,
    autoplay: items.length > 1,
    autoplaySpeed: 4000,
    pauseOnHover: true,
    speed: 500,
    slidesToShow: 3,
    slidesToScroll: 1,
    arrows: items.length > 1,
    responsive: [
      {
        breakpoint: 900,
        settings: { slidesToShow: 2, infinite: items.length > 2 },
      },
      {
        breakpoint: 600,
        settings: { slidesToShow: 1, infinite: items.length > 1 },
      },
    ],
  };

  return (
    <Stack
      spacing={0.75}
      sx={{
        width: "100%",
        // Use slick's native float-based layout. Override only padding for
        // gutter and dots position. Track widths/positions are computed by
        // slick — do NOT touch them.
        "& .slick-slide > div": { padding: "0 4px" },
        "& .slick-dots": { position: "static", mt: 1 },
      }}
    >
      <Stack
        direction="row"
        spacing={0.5}
        className="rgl-cancel"
        sx={{
          flexWrap: "nowrap",
          overflowX: "auto",
          overflowY: "hidden",
          pb: 0.5,
          "&::-webkit-scrollbar": { height: 4 },
          "&::-webkit-scrollbar-thumb": {
            bgcolor: "var(--joy-palette-neutral-300, #d4d4d4)",
            borderRadius: 4,
          },
          scrollbarWidth: "thin",
          "& > *": { flexShrink: 0 },
        }}
      >
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
        {subgroups.map((sg) => (
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
        <Box
          sx={{
            width: "100%",
            px: 3,
            "& .slick-slider": { width: "100%" },
            "& .slick-prev": { left: -22, zIndex: 2 },
            "& .slick-next": { right: -22, zIndex: 2 },
            "& .slick-prev:before, & .slick-next:before": {
              color: "var(--joy-palette-text-secondary, #555)",
              fontSize: 22,
            },
            "& .slick-dots li button:before": {
              color: "var(--joy-palette-text-tertiary, #888)",
            },
          }}
        >
          {/* key forces re-init when scope/data length changes (slick caches DOM measurements) */}
          <Slider key={`${scope.kind}-${items.length}`} {...sliderSettings}>
            {items.map((item) => {
              const isImage = item.media.content_type.startsWith("image/");
              const href =
                item.source === "post"
                  ? `/app/post/${item.source_id}`
                  : `/app/galleries/${item.source_id}`;
              return (
                <div key={item.media_id}>
                  <Link
                    href={href}
                    aria-label={item.source_title ?? "Media item"}
                    className="block relative w-full overflow-hidden rounded-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)]"
                    style={{ height: 280, background: "transparent" }}
                  >
                    {isImage ? (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img
                        // Pick endpoint at render time. onError fallback
                        // does NOT survive slick's DOM cloning for infinite
                        // mode (clones are deep-cloned without React handlers),
                        // so use /file when the row has no thumbnail_key.
                        src={`${API_BASE}/api/v1/media/${item.media.id}/${item.media.thumbnail_key ? "thumbnail" : "file"}`}
                        alt={item.media.alt_text ?? item.source_title ?? ""}
                        style={{
                          position: "absolute",
                          inset: 0,
                          width: "100%",
                          height: "100%",
                          objectFit: "contain",
                          objectPosition: "center",
                          background: "transparent",
                        }}
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
                </div>
              );
            })}
          </Slider>
        </Box>
      )}
    </Stack>
  );
}

export default MediaCarouselWidget;
