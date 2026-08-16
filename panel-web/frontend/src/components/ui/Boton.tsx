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
        "inline-flex h-11 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold",
        "transition-colors disabled:opacity-50",
        variante === "primario" && "bg-accent text-white hover:bg-accent-hover",
        variante === "secundario" &&
          "bg-card text-ink shadow-sm ring-1 ring-[var(--ring)] hover:bg-card-soft",
        variante === "fantasma" && "text-ink-2 hover:text-ink",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
