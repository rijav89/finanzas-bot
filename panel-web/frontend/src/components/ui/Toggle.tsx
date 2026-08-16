import { cn } from "@/lib/cn";

/** Switch estilo iOS del mockup de Recurrentes. */
export function Toggle({
  activo,
  onChange,
  etiqueta,
  disabled,
}: {
  activo: boolean;
  onChange: (v: boolean) => void;
  etiqueta: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={activo}
      aria-label={etiqueta}
      disabled={disabled}
      onClick={() => onChange(!activo)}
      className={cn(
        "relative h-7 w-12 shrink-0 rounded-full transition-colors disabled:opacity-50",
        activo ? "bg-accent" : "bg-card-soft ring-1 ring-inset ring-[var(--ring)]",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "absolute top-1 size-5 rounded-full bg-white shadow-sm transition-[left]",
          activo ? "left-6" : "left-1",
        )}
      />
    </button>
  );
}
