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
  arrayMove,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import type { ReactNode } from "react";

import { useBentoStore, type WidgetId } from "@/stores/bentoStore";

export function BentoGrid({
  children,
  ids,
}: {
  children: ReactNode;
  ids: WidgetId[];
}) {
  const setOrden = useBentoStore((s) => s.setOrden);
  const sensores = useSensors(
    // Distancia mínima: evita que un tap en el botón de expandir inicie un arrastre
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function alSoltar({ active, over }: DragEndEvent) {
    if (!over || active.id === over.id) return;
    const desde = ids.indexOf(active.id as WidgetId);
    const hasta = ids.indexOf(over.id as WidgetId);
    if (desde < 0 || hasta < 0) return;
    setOrden(arrayMove(ids, desde, hasta));
  }

  return (
    <DndContext sensors={sensores} collisionDetection={closestCenter} onDragEnd={alSoltar}>
      <SortableContext items={ids} strategy={rectSortingStrategy}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">{children}</div>
      </SortableContext>
    </DndContext>
  );
}
