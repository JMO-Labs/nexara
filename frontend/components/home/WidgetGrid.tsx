"use client";
/**
 * @file components/home/WidgetGrid.tsx
 * @brief Drag-and-drop responsive grid for home page widgets.
 *        Uses @dnd-kit/sortable for keyboard-accessible reordering.
 *        Grid: 12-col on lg, 6-col on md, 1-col on xs.
 *        Size map: sm=3col, md=6col, lg=9col, full=12col.
 * @param widgets  Sorted widget instances from useHomeLayout.
 * @param onReorder Callback with new id order after drag.
 * @param onRemove  Callback to remove a widget instance.
 * @param onToggleCollapsed Callback to toggle widget collapse.
 * @param isLoading Show skeleton cells while layout is loading.
 */
import * as React from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { getDef } from "@/lib/widgets/registry";
import { WidgetFrame } from "./WidgetFrame";
import { Skeleton } from "@/components/ui/Skeleton";
import type { WidgetInstance } from "@/lib/widgets/registry";

// ---------------------------------------------------------------------------
// Size → col-span map
// ---------------------------------------------------------------------------

const SIZE_SPAN: Record<WidgetInstance["size"], string> = {
  sm: "col-span-12 md:col-span-6 lg:col-span-3",
  md: "col-span-12 md:col-span-6",
  lg: "col-span-12 lg:col-span-9",
  full: "col-span-12",
};

// ---------------------------------------------------------------------------
// Drag handle icon
// ---------------------------------------------------------------------------

function GripIcon() {
  return (
    <svg
      aria-hidden="true"
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="currentColor"
      className="text-neutral-400"
    >
      <circle cx="4" cy="3" r="1" />
      <circle cx="10" cy="3" r="1" />
      <circle cx="4" cy="7" r="1" />
      <circle cx="10" cy="7" r="1" />
      <circle cx="4" cy="11" r="1" />
      <circle cx="10" cy="11" r="1" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// SortableWidget — wrapper for each draggable widget cell
// ---------------------------------------------------------------------------

interface SortableWidgetProps {
  widget: WidgetInstance;
  onRemove: (id: string) => void;
  onToggleCollapsed: (id: string) => void;
}

function SortableWidget({
  widget,
  onRemove,
  onToggleCollapsed,
}: SortableWidgetProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: widget.id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const def = getDef(widget.defId);
  if (!def) {
    return null;
  }

  const DragHandle = (
    <button
      type="button"
      aria-label="Drag to reorder widget"
      className="cursor-grab active:cursor-grabbing p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--nx-palette-focusVisible,#4f46e5)]"
      {...attributes}
      {...listeners}
    >
      <GripIcon />
    </button>
  );

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={SIZE_SPAN[widget.size]}
    >
      <WidgetFrame
        title={def.title}
        collapsed={widget.collapsed}
        onToggleCollapsed={() => onToggleCollapsed(widget.id)}
        onRemove={() => onRemove(widget.id)}
        dragHandleSlot={DragHandle}
        size={widget.size}
      >
        <def.Component instanceId={widget.id} props={widget.props} />
      </WidgetFrame>
    </div>
  );
}

// ---------------------------------------------------------------------------
// WidgetGrid
// ---------------------------------------------------------------------------

export interface WidgetGridProps {
  widgets: WidgetInstance[];
  onReorder: (newIds: string[]) => void;
  onRemove: (instanceId: string) => void;
  onToggleCollapsed: (instanceId: string) => void;
  isLoading?: boolean;
}

export function WidgetGrid({
  widgets,
  onReorder,
  onRemove,
  onToggleCollapsed,
  isLoading = false,
}: WidgetGridProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = widgets.findIndex((w) => w.id === active.id);
    const newIndex = widgets.findIndex((w) => w.id === over.id);
    if (oldIndex === -1 || newIndex === -1) return;

    const reordered = [...widgets];
    const [moved] = reordered.splice(oldIndex, 1);
    reordered.splice(newIndex, 0, moved);
    onReorder(reordered.map((w) => w.id));
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-12 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="col-span-12 md:col-span-6 lg:col-span-3">
            <Skeleton height={200} rounded="md" />
          </div>
        ))}
      </div>
    );
  }

  const ids = widgets.map((w) => w.id);

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext items={ids} strategy={verticalListSortingStrategy}>
        <div className="grid grid-cols-12 gap-4">
          {widgets
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((widget) => (
              <SortableWidget
                key={widget.id}
                widget={widget}
                onRemove={onRemove}
                onToggleCollapsed={onToggleCollapsed}
              />
            ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}

export default WidgetGrid;
