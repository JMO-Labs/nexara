"use client";
/**
 * @file components/home/WidgetColumn.tsx
 * @brief Right-hand widget column: sortable (pointer + keyboard) and
 *        customizable (show/hide) via useHomeLayout.
 */
import * as React from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, SlidersHorizontal } from "lucide-react";
import { Button, IconButton } from "@/components/ui";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/shadcn/dropdown-menu";
import { useHomeLayout } from "@/hooks/useHomeLayout";
import { WIDGETS } from "./widgetRegistry";
import { WidgetFrame } from "./WidgetFrame";

type Def = (typeof WIDGETS)[number];

function SortableWidget({ def, index }: { def: Def; index: number }) {
  const s = useSortable({ id: def.id });
  const { Component } = def;
  return (
    <div
      ref={s.setNodeRef}
      data-index={index}
      style={{
        transform: CSS.Transform.toString(s.transform),
        transition: s.transition,
      }}
      className={s.isDragging ? "opacity-70 relative z-10" : undefined}
    >
      <WidgetFrame
        title={def.title}
        actions={
          <IconButton
            ref={s.setActivatorNodeRef}
            variant="ghost"
            size="sm"
            aria-label={`Reorder ${def.title}`}
            {...s.attributes}
            {...s.listeners}
          >
            <GripVertical aria-hidden className="size-4" />
          </IconButton>
        }
      >
        <Component />
      </WidgetFrame>
    </div>
  );
}

/**
 * @brief Sortable widget sidebar (hidden below md).
 * @return aside element
 */
export function WidgetColumn() {
  const { order, hidden, move, toggle } = useHomeLayout();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  const visible = order
    .filter((id) => !hidden.includes(id))
    .map((id) => WIDGETS.find((w) => w.id === id))
    .filter((w): w is Def => !!w);
  const ids = visible.map((w) => w.id);

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    move(
      order.indexOf(active.id as Def["id"]),
      order.indexOf(over.id as Def["id"]),
    );
  };

  return (
    <aside
      aria-label="Widgets"
      className="hidden md:flex flex-col w-[300px] gap-4"
    >
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={onDragEnd}
      >
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          {visible.map((def, i) => (
            <SortableWidget key={def.id} def={def} index={i} />
          ))}
        </SortableContext>
      </DndContext>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="self-start">
            <SlidersHorizontal aria-hidden className="size-4" />
            Customize
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          {WIDGETS.map((w) => (
            <DropdownMenuCheckboxItem
              key={w.id}
              checked={!hidden.includes(w.id)}
              onCheckedChange={() => toggle(w.id)}
            >
              {w.title}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </aside>
  );
}

export default WidgetColumn;
