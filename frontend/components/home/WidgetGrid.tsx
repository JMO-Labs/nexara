"use client";
/**
 * @file components/home/WidgetGrid.tsx
 * @brief Dashboard grid powered by react-grid-layout (legacy entry).
 *        - Drag-to-reorder anywhere on the widget except `.rgl-cancel`.
 *        - Free-form resize via the bottom-right grip.
 *        - Persists positions via useHomeLayout.applyLayout.
 *
 *        Uses non-responsive ReactGridLayout + WidthProvider so the layout
 *        prop is the single source of truth (responsive variant maintains
 *        per-breakpoint state and was sending stale rows back through
 *        onLayoutChange when children changed).
 */
import * as React from "react";
import RGL, {
  WidthProvider,
  type Layout,
  type LayoutItem,
} from "react-grid-layout/legacy";
import { getDef } from "@/lib/widgets/registry";
import { GRID_COLS, GRID_ROW_HEIGHT, type WidgetInstance } from "@/lib/widgets/registry";
import { WidgetFrame } from "./WidgetFrame";
import { Skeleton } from "@/components/ui/Skeleton";
import { useWidgetDrag } from "@/stores/widgetDrag";

import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

const ReactGridLayout = WidthProvider(RGL);

const DRAG_CANCEL = ".rgl-cancel,button,a,input,textarea,select,[role=slider]";

export interface WidgetGridProps {
  widgets: WidgetInstance[];
  onApplyLayout: (
    items: Array<{ i: string; x: number; y: number; w: number; h: number }>,
  ) => void;
  onRemove: (instanceId: string) => void;
  onToggleCollapsed: (instanceId: string) => void;
  isLoading?: boolean;
}

export function WidgetGrid({
  widgets,
  onApplyLayout,
  onRemove,
  onToggleCollapsed,
  isLoading = false,
}: WidgetGridProps) {
  const dragDisabledIds = useWidgetDrag((s) => s.disabledIds);

  const layout: Layout = React.useMemo<Layout>(
    () =>
      widgets.map<LayoutItem>((w) => {
        const def = getDef(w.defId);
        // Collapsed widgets render at h=1 (header only). Persisted h stays
        // intact so expand restores the previous height.
        const renderedH = w.collapsed ? 1 : w.h;
        return {
          i: w.id,
          x: w.x,
          y: w.y,
          w: w.w,
          h: renderedH,
          minW: def?.minW ?? 2,
          minH: w.collapsed ? 1 : (def?.minH ?? 2),
          maxH: w.collapsed ? 1 : undefined,
          isDraggable: !dragDisabledIds.has(w.id),
          isResizable: !w.collapsed && !dragDisabledIds.has(w.id),
        };
      }),
    [widgets, dragDisabledIds],
  );

  // Only fire applyLayout for user-initiated drag/resize end events, not for
  // every internal RGL onLayoutChange (which may emit stale rows on children
  // changes). We persist on dragStop and resizeStop only.
  const widgetsById = React.useMemo(() => {
    const m = new Map<string, WidgetInstance>();
    for (const w of widgets) m.set(w.id, w);
    return m;
  }, [widgets]);

  // Guard: only persist layout when an interaction was actually started by
  // the user. RGL otherwise emits Stop events on internal reflows (collapse
  // toggles, prop-driven h changes) which would overwrite stored heights.
  const userInteractingRef = React.useRef(false);

  const handleStart = React.useCallback(() => {
    userInteractingRef.current = true;
  }, []);

  const persistLayout = React.useCallback(
    (newLayout: Layout) => {
      if (!userInteractingRef.current) return;
      userInteractingRef.current = false;
      onApplyLayout(
        newLayout.map((l) => {
          const stored = widgetsById.get(l.i);
          // Preserve stored h on collapsed widgets so expand restores height.
          const h = stored?.collapsed ? stored.h : l.h;
          return { i: l.i, x: l.x, y: l.y, w: l.w, h };
        }),
      );
    },
    [onApplyLayout, widgetsById],
  );

  if (isLoading) {
    return (
      <div className="grid grid-cols-12 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} style={{ gridColumn: "span 3 / span 3" }}>
            <Skeleton height={200} rounded="md" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <ReactGridLayout
      className="layout"
      layout={layout}
      cols={GRID_COLS}
      rowHeight={GRID_ROW_HEIGHT}
      margin={[12, 12]}
      containerPadding={[0, 0]}
      onDragStart={handleStart}
      onDragStop={persistLayout}
      onResizeStart={handleStart}
      onResizeStop={persistLayout}
      draggableCancel={DRAG_CANCEL}
      resizeHandles={["se"]}
      compactType="vertical"
      preventCollision={false}
      autoSize
    >
      {widgets.map((widget) => {
        const def = getDef(widget.defId);
        if (!def) return null;
        return (
          <div key={widget.id}>
            <WidgetFrame
              title={def.title}
              collapsed={widget.collapsed}
              onToggleCollapsed={() => onToggleCollapsed(widget.id)}
              onRemove={() => onRemove(widget.id)}
            >
              <def.Component instanceId={widget.id} props={widget.props} />
            </WidgetFrame>
          </div>
        );
      })}
    </ReactGridLayout>
  );
}

export default WidgetGrid;
