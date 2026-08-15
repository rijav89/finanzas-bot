import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Card({
  children,
  className,
  ...props
}: { children: ReactNode; className?: string } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl bg-card p-4 ring-1 ring-[var(--border-ring)] sm:p-5",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardTitulo({ children }: { children: ReactNode }) {
  return (
    <h2 className="text-sm font-medium text-ink-2">{children}</h2>
  );
}
