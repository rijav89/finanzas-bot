import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";

import { cn } from "@/lib/cn";

export type Estado = "good" | "warning" | "serious" | "critical" | "info";

const CONFIG: Record<Estado, { color: string; Icono: typeof Info; etiqueta: string }> = {
  good: { color: "text-good-text", Icono: CheckCircle2, etiqueta: "En orden" },
  warning: { color: "text-warning", Icono: AlertTriangle, etiqueta: "Atención" },
  serious: { color: "text-serious", Icono: AlertTriangle, etiqueta: "Cuidado" },
  critical: { color: "text-critical", Icono: XCircle, etiqueta: "Crítico" },
  info: { color: "text-ink-3", Icono: Info, etiqueta: "Info" },
};

/** Estado nunca por color solo: siempre icono + etiqueta (requisito de accesibilidad). */
export function Semaforo({
  estado,
  etiqueta,
  className,
}: {
  estado: Estado;
  etiqueta?: string;
  className?: string;
}) {
  const { color, Icono, etiqueta: porDefecto } = CONFIG[estado];
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", color, className)}>
      <Icono size={14} aria-hidden />
      {etiqueta ?? porDefecto}
    </span>
  );
}
