import { X } from "lucide-react";
import { useEffect, type ReactNode } from "react";

/** Hoja modal compartida: bottom sheet en móvil, diálogo centrado en escritorio.
 *  Cabecera fija y cuerpo scrolleable para convivir con el teclado virtual. */
export function Hoja({
  titulo,
  subtitulo,
  onCerrar,
  children,
  ancho = "max-w-lg",
}: {
  titulo: string;
  subtitulo?: string;
  onCerrar: () => void;
  children: ReactNode;
  ancho?: string;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCerrar();
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
    };
  }, [onCerrar]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 backdrop-blur-[2px] sm:items-center sm:p-4"
      onClick={onCerrar}
    >
      <div
        role="dialog"
        aria-label={titulo}
        onClick={(e) => e.stopPropagation()}
        className={`flex max-h-[92dvh] w-full ${ancho} flex-col rounded-t-2xl bg-card shadow-2xl sm:max-h-[88dvh] sm:rounded-2xl`}
      >
        <header className="flex shrink-0 items-start gap-3 border-b border-hairline px-5 py-4">
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-lg font-bold tracking-tight">{titulo}</h2>
            {subtitulo && <p className="mt-0.5 text-sm text-ink-2">{subtitulo}</p>}
          </div>
          <button
            onClick={onCerrar}
            aria-label="Cerrar"
            className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-card-soft text-ink-2 transition-colors hover:text-ink"
          >
            <X size={18} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] sm:pb-5">
          {children}
        </div>
      </div>
    </div>
  );
}
