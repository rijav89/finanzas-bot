import { cn } from "@/lib/cn";

export type TonoBarra = "good" | "warn" | "bad" | "accent" | "serie";

const COLORES: Record<TonoBarra, string> = {
  good: "var(--good)",
  warn: "var(--warn)",
  bad: "var(--bad)",
  accent: "var(--accent)",
  serie: "var(--s1)",
};

/** Barra sobre riel gris, como el mockup. `color` acepta un tono o un CSS var de serie. */
export function BarraProgreso({
  porcentaje,
  tono = "accent",
  color,
  altura = "h-2",
  className,
}: {
  porcentaje: number;
  tono?: TonoBarra;
  /** Override directo (ej. "var(--s2)") para barras por categoría. */
  color?: string;
  altura?: string;
  className?: string;
}) {
  const ancho = Math.min(Math.max(porcentaje, 0), 100);
  return (
    <div
      className={cn("overflow-hidden rounded-full bg-card-soft", altura, className)}
      role="progressbar"
      aria-valuenow={Math.round(porcentaje)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="h-full rounded-full transition-[width] duration-300"
        style={{ width: `${ancho}%`, background: color ?? COLORES[tono] }}
      />
    </div>
  );
}
