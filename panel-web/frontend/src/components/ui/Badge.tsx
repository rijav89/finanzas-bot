import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Tono = "good" | "warn" | "bad" | "accent" | "neutro";

const TONOS: Record<Tono, string> = {
  good: "bg-good-soft text-good-ink",
  warn: "bg-warn-soft text-warn-ink",
  bad: "bg-bad-soft text-bad-ink",
  accent: "bg-accent-soft text-accent-ink",
  neutro: "bg-card-soft text-ink-2",
};

const PUNTOS: Record<Tono, string> = {
  good: "bg-good",
  warn: "bg-warn",
  bad: "bg-bad",
  accent: "bg-accent",
  neutro: "bg-ink-3",
};

/** Pastilla de estado del mockup: punto de color + texto, fondo suave. */
export function Badge({
  tono = "neutro",
  punto = true,
  children,
  className,
}: {
  tono?: Tono;
  punto?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
        TONOS[tono],
        className,
      )}
    >
      {punto && <span aria-hidden className={cn("size-1.5 rounded-full", PUNTOS[tono])} />}
      {children}
    </span>
  );
}
