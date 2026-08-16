import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/** Superficie base del diseño: blanca, esquinas 16px, borde hairline y sombra mínima. */
export function Card({
  children,
  className,
  padding = "p-5",
}: {
  children: ReactNode;
  className?: string;
  padding?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-2xl bg-card shadow-[0_1px_2px_rgba(17,24,39,0.04)] ring-1 ring-[var(--ring)]",
        padding,
        className,
      )}
    >
      {children}
    </section>
  );
}

/** Cabecera de página: título grande, subtítulo y acciones a la derecha. */
export function PageHeader({
  titulo,
  subtitulo,
  acciones,
}: {
  titulo: string;
  subtitulo?: ReactNode;
  acciones?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start gap-3 pb-5 pt-1 lg:pb-6">
      <div className="min-w-0 flex-1">
        <h1 className="text-2xl font-bold tracking-tight lg:text-[2rem] lg:leading-tight">
          {titulo}
        </h1>
        {subtitulo && <p className="mt-1 text-sm text-ink-2">{subtitulo}</p>}
      </div>
      {acciones && <div className="flex shrink-0 items-center gap-2">{acciones}</div>}
    </header>
  );
}
