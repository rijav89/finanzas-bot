import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronDown, GripVertical } from "lucide-react";
import { useState, type ReactNode } from "react";

import { cn } from "@/lib/cn";

interface Props {
  id: string;
  titulo: string;
  /** Métrica en superficie; el desglose se revela al expandir (progressive disclosure). */
  children: ReactNode;
  desglose?: ReactNode;
  className?: string;
  arrastrable?: boolean;
}

export function BentoCard({
  id,
  titulo,
  children,
  desglose,
  className,
  arrastrable = true,
}: Props) {
  const [abierto, setAbierto] = useState(false);
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
        "rounded-2xl bg-card p-4 ring-1 ring-[var(--border-ring)] sm:p-5",
        isDragging && "z-10 opacity-80 shadow-xl",
        className,
      )}
    >
      <header className="flex items-center gap-2">
        <h2 className="text-sm font-medium text-ink-2">{titulo}</h2>
        {desglose && (
          <button
            onClick={() => setAbierto((v) => !v)}
            aria-expanded={abierto}
            className="ml-auto text-ink-3 hover:text-ink-2"
          >
            <ChevronDown
              size={18}
              className={cn("transition-transform", abierto && "rotate-180")}
            />
          </button>
        )}
        {arrastrable && (
          <button
            {...attributes}
            {...listeners}
            aria-label={`Reordenar ${titulo}`}
            className={cn(
              "cursor-grab touch-none text-ink-3 hover:text-ink-2 active:cursor-grabbing",
              !desglose && "ml-auto",
            )}
          >
            <GripVertical size={18} />
          </button>
        )}
      </header>

      <div className="mt-3">{children}</div>

      {desglose && abierto && (
        <div className="mt-4 border-t border-hairline pt-4">{desglose}</div>
      )}
    </section>
  );
}
