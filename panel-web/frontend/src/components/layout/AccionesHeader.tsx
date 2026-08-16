import { Bell, Plus } from "lucide-react";

import { useUiStore } from "@/stores/uiStore";

/** Campana + botón primario que aparecen a la derecha del título en escritorio. */
export function AccionesHeader({ etiqueta = "Nuevo movimiento" }: { etiqueta?: string }) {
  const abrirCaptura = useUiStore((s) => s.abrirCaptura);
  const setPaleta = useUiStore((s) => s.setPaletaAbierta);

  return (
    <>
      <button
        aria-label="Buscar (Ctrl K)"
        onClick={() => setPaleta(true)}
        className="flex size-11 items-center justify-center rounded-xl bg-card text-ink-2 shadow-sm ring-1 ring-[var(--ring)] transition-colors hover:text-ink"
      >
        <Bell size={18} />
      </button>
      <button
        onClick={() => abrirCaptura("gasto")}
        className="inline-flex h-11 items-center gap-2 rounded-xl bg-accent px-4 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
      >
        <Plus size={18} />
        {etiqueta}
      </button>
    </>
  );
}
