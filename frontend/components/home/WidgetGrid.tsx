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
  // Measure on mount via a ref callback (fires before paint, before
  // useEffect) so the very first render of <GridLayout/> already knows the
  // correct width. ResizeObserver re-measures on viewport / sidebar shifts.
  const [width, setWidth] = React.useState(0);
  const observerRef = React.useRef<ResizeObserver | null>(null);
  const containerRef = React.useCallback((node: HTMLDivElement | null) => {
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
    if (!node) return;
    setWidth(node.getBoundingClientRect().width);
    if (typeof ResizeObserver === "undefined") return;
    let raf: number | null = null;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? 0;
      if (w <= 0) return;
      if (raf !== null) cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => setWidth(w));
    });
    ro.observe(node);
    observerRef.current = ro;
  }, []);
  const mounted = width > 0;

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

  // RGL v2's onDragStop / onResizeStop only fire on user-completed
  // interactions, so we can persist directly. Stash the latest widgetsById
  // in a ref so the persist callback never goes stale between drags
  // (its useCallback identity would otherwise change every time `widgets`
  // mutates, churning the inline arrow we hand to <GridLayout>).
  const widgetsByIdRef = React.useRef(widgetsById);
  React.useEffect(() => {
    widgetsByIdRef.current = widgetsById;
  }, [widgetsById]);
  const onApplyLayoutRef = React.useRef(onApplyLayout);
  React.useEffect(() => {
    onApplyLayoutRef.current = onApplyLayout;
  }, [onApplyLayout]);

  const persistOnStop = React.useCallback((newLayout: Layout) => {
    onApplyLayoutRef.current(
      newLayout.map((l) => {
        const stored = widgetsByIdRef.current.get(l.i);
        const h = stored?.collapsed ? stored.h : l.h;
        return { i: l.i, x: l.x, y: l.y, w: l.w, h };
      }),
    );
  }, []);
  // Stable config objects — RGL re-runs sync effects when these deep-change.
  const gridConfig = React.useMemo(
    () => ({
      cols: GRID_COLS,
      rowHeight: GRID_ROW_HEIGHT,
      margin: [12, 12] as [number, number],
      containerPadding: [0, 0] as [number, number],
      maxRows: Infinity,
    }),
    [],
  );
  const dragConfig = React.useMemo(
    () => ({
      enabled: true,
      bounded: false,
      cancel: DRAG_CANCEL,
      threshold: 3,
    }),
    [],
  );
  const resizeConfig = React.useMemo(
    () => ({ enabled: true, handles: ["se"] as const }),
    [],
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
    <div ref={containerRef} style={{ width: "100%", maxWidth: "100%", minWidth: 0 }}>
      {mounted && (
        <GridLayout
          width={width}
          layout={layout}
          gridConfig={gridConfig}
          dragConfig={dragConfig}
          resizeConfig={resizeConfig}
          compactor={verticalCompactor}
          autoSize
          onDragStop={persistOnStop}
          onResizeStop={persistOnStop}
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
