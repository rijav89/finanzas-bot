import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variante?: "primario" | "secundario" | "fantasma";
}

export function Boton({ children, variante = "primario", className, ...props }: Props) {
  return (
    <button
      className={cn(
        "inline-flex touch-44 items-center justify-center gap-2 rounded-xl px-4 text-sm font-medium",
        "transition-opacity disabled:opacity-50",
        variante === "primario" && "bg-accent text-white hover:opacity-90",
        variante === "secundario" &&
          "bg-card text-ink ring-1 ring-[var(--border-ring)] hover:opacity-90",
        variante === "fantasma" && "text-ink-2 hover:text-ink",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
