"use client";
/**
 * @file components/home/WidgetGrid.tsx
 * @brief Dashboard grid powered by react-grid-layout v2.
 *        - useContainerWidth hook measures the wrapper element.
 *        - gridConfig / dragConfig / resizeConfig group related props.
 *        - persistLayout fires only on user-initiated drag/resize so the
 *          collapse toggle (which mutates item.h via props) does not race.
 */
import * as React from "react";
import GridLayout, {
  useContainerWidth,
  verticalCompactor,
  type Layout,
  type LayoutItem,
} from "react-grid-layout";
import { getDef } from "@/lib/widgets/registry";
import {
  GRID_COLS,
  GRID_ROW_HEIGHT,
  type WidgetInstance,
} from "@/lib/widgets/registry";
import { WidgetFrame } from "./WidgetFrame";
import { Skeleton } from "@/components/ui/Skeleton";
import { useWidgetDrag } from "@/stores/widgetDrag";

import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

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
  // measureBeforeMount: true so we don't render with the default 1280px
  // width and overflow / underflow the actual container. Eliminates the
  // first-paint "widgets too narrow / too wide" jump.
  const { width, containerRef, mounted } = useContainerWidth({
    measureBeforeMount: true,
  });

  // Filter out widgets whose def is not registered — keeps the children
  // array, layout array, and onLayoutChange events in lock-step (RGL gets
  // confused if layout and children diverge in length).
  const validWidgets = React.useMemo(
    () => widgets.filter((w) => getDef(w.defId) !== undefined),
    [widgets],
  );

  const layout: Layout = React.useMemo<Layout>(
    () =>
      validWidgets.map<LayoutItem>((w) => {
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
    [validWidgets, dragDisabledIds],
  );

  const widgetsById = React.useMemo(() => {
    const m = new Map<string, WidgetInstance>();
    for (const w of validWidgets) m.set(w.id, w);
    return m;
  }, [validWidgets]);

  // Guard: only persist on user-initiated drag/resize. RGL also fires Stop
  // events on internal reflows triggered by prop changes (e.g. collapse).
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
    <div ref={containerRef} style={{ width: "100%" }}>
      {mounted && (
        <GridLayout
          width={width}
          layout={layout}
          gridConfig={{
            cols: GRID_COLS,
            rowHeight: GRID_ROW_HEIGHT,
            margin: [12, 12],
            containerPadding: [0, 0],
            maxRows: Infinity,
          }}
          dragConfig={{
            enabled: true,
            bounded: false,
            cancel: DRAG_CANCEL,
            threshold: 3,
          }}
          resizeConfig={{
            enabled: true,
            handles: ["se"],
          }}
          compactor={verticalCompactor}
          autoSize
          onDragStart={handleStart}
          onDragStop={persistLayout}
          onResizeStart={handleStart}
          onResizeStop={persistLayout}
        >
          {validWidgets.map((widget) => {
            const def = getDef(widget.defId)!;
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
        </GridLayout>
      )}
    </div>
  );
}

export default WidgetGrid;
