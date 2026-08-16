import type { Semaforo } from "@/api/types";
import { cn } from "@/lib/cn";

const COLOR: Record<Semaforo, string> = {
  bien: "var(--status-good)",
  atencion: "var(--status-warning)",
  critico: "var(--status-critical)",
  info: "var(--series-1)",
};

/** Barra sobre riel: la longitud se lee como proporción, no como valor suelto.
 *  El color nunca va solo — siempre acompañado del texto del porcentaje. */
export function BarraProgreso({
  porcentaje,
  estado = "info",
  className,
}: {
  porcentaje: number;
  estado?: Semaforo;
  className?: string;
}) {
  const ancho = Math.min(Math.max(porcentaje, 0), 100);
  return (
    <div
      className={cn("h-2 overflow-hidden rounded-full bg-page", className)}
      role="progressbar"
      aria-valuenow={Math.round(porcentaje)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full transition-[width]"
        style={{ width: `${ancho}%`, background: COLOR[estado] }}
      />
    </div>
  );
}
