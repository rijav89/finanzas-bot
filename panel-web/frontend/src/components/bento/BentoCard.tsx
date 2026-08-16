import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface Props {
  id: string;
  titulo: string;
  subtitulo?: string;
  children: ReactNode;
  className?: string;
  arrastrable?: boolean;
}

/** Tarjeta del Bento: título gris arriba a la izquierda, asa de arrastre a la derecha. */
export function BentoCard({
  id,
  titulo,
  subtitulo,
  children,
  className,
  arrastrable = true,
}: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
    disabled: !arrastrable,
  });

  return (
    // Este <section> ES la celda del grid (className trae el col-span): dnd-kit
    // debe medir y transformar el mismo elemento que la grilla posiciona.
    <section
      ref={setNodeRef}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      className={cn(
        "rounded-2xl bg-card p-5 shadow-[0_1px_2px_rgba(17,24,39,0.04)] ring-1 ring-[var(--ring)]",
        isDragging && "z-10 opacity-90 shadow-xl",
        className,
      )}
    >
      <header className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <h2 className="text-[15px] font-medium text-ink-2">{titulo}</h2>
          {subtitulo && <p className="mt-1 text-sm text-ink-3">{subtitulo}</p>}
        </div>
        {arrastrable && (
          <button
            {...attributes}
            {...listeners}
            aria-label={`Reordenar ${titulo}`}
            className="-mr-1 -mt-1 cursor-grab touch-none rounded-lg p-1 text-ink-3/70 transition-colors hover:text-ink-2 active:cursor-grabbing"
          >
            <GripVertical size={16} />
          </button>
        )}
      </header>

      {children}
    </section>
  );
}
