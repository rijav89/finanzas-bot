import { ArrowDownLeft, ArrowUpRight, ChevronDown } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { useCrearMovimiento, useCuentas } from "@/api/queries";
import { CATEGORIAS, CATEGORIAS_INGRESO } from "@/api/types";
import { Boton } from "@/components/ui/Boton";
import { cn } from "@/lib/cn";
import { useUiStore, type TipoMovimiento } from "@/stores/uiStore";

/** Captura conversacional "Mad Libs" para gastos e ingresos.
 *
 *  Layout: bottom sheet en móvil / diálogo centrado en desktop, con cabecera y
 *  acciones fijas y cuerpo scrolleable — así el teclado virtual nunca tapa el
 *  monto ni el botón de confirmar. */
export function CapturaRapida() {
  const tipoInicial = useUiStore((s) => s.captura);
  const cerrar = useUiStore((s) => s.cerrarCaptura);
  const { data: cuentas } = useCuentas();
  const crear = useCrearMovimiento();
  const montoRef = useRef<HTMLInputElement>(null);

  const [tipo, setTipo] = useState<TipoMovimiento>("gasto");
  const [monto, setMonto] = useState("");
  const [categoria, setCategoria] = useState<string>(CATEGORIAS[0]);
  const [cuentaId, setCuentaId] = useState<number | null>(null);
  const [fecha, setFecha] = useState(hoyISO);
  const [nota, setNota] = useState("");

  const abierto = tipoInicial !== null;

  // Reset al abrir: la pestaña la decide quien dispara (FAB, paleta de comandos)
  useEffect(() => {
    if (!abierto) return;
    setTipo(tipoInicial);
    setCategoria(tipoInicial === "gasto" ? CATEGORIAS[0] : CATEGORIAS_INGRESO[0]);
    setMonto("");
    setNota("");
    setFecha(hoyISO());
    crear.reset();
    // crear.reset es estable; solo interesa reaccionar a la apertura
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto, tipoInicial]);

  useEffect(() => {
    if (cuentas?.length && cuentaId === null) {
      setCuentaId((cuentas.find((c) => c.es_principal) ?? cuentas[0]).id);
    }
  }, [cuentas, cuentaId]);

  // Escape cierra; bloquear scroll del fondo mientras está abierto
  useEffect(() => {
    if (!abierto) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && cerrar();
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
    };
  }, [abierto, cerrar]);

  const categorias = tipo === "gasto" ? CATEGORIAS : CATEGORIAS_INGRESO;
  const montoValido = Number(monto) > 0;

  const cuentasOpts = useMemo(
    () => (cuentas ?? []).map((c) => ({ valor: String(c.id), etiqueta: c.nombre })),
    [cuentas],
  );

  if (!abierto) return null;

  function cambiarTipo(nuevo: TipoMovimiento) {
    setTipo(nuevo);
    setCategoria(nuevo === "gasto" ? CATEGORIAS[0] : CATEGORIAS_INGRESO[0]);
    montoRef.current?.focus();
  }

  const esGasto = tipo === "gasto";

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4"
      onClick={cerrar}
    >
      <form
        role="dialog"
        aria-label={esGasto ? "Registrar gasto" : "Registrar ingreso"}
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          if (!montoValido || cuentaId === null) return;
          crear.mutate(
            {
              tipo,
              monto,
              categoria,
              cuenta_id: cuentaId,
              fecha,
              ...(nota.trim() ? { descripcion: nota.trim() } : {}),
            },
            { onSuccess: cerrar },
          );
        }}
        className="flex max-h-[94dvh] w-full max-w-lg flex-col rounded-t-2xl bg-card shadow-2xl ring-1 ring-[var(--border-ring)] sm:max-h-[88dvh] sm:rounded-2xl"
      >
        {/* ── Cabecera fija: tipo + monto ── */}
        <div className="shrink-0 px-4 pt-3 sm:px-6 sm:pt-5">
          {/* Asa del bottom sheet (solo móvil) */}
          <div
            aria-hidden
            className="mx-auto mb-3 h-1 w-9 rounded-full bg-ink-3/30 sm:hidden"
          />

          <div
            role="tablist"
            aria-label="Tipo de movimiento"
            className="mx-auto flex w-full max-w-[17rem] rounded-lg bg-page p-1"
          >
            {(
              [
                { valor: "gasto", etiqueta: "Gasto", Icono: ArrowUpRight },
                { valor: "ingreso", etiqueta: "Ingreso", Icono: ArrowDownLeft },
              ] as const
            ).map(({ valor, etiqueta, Icono }) => {
              const activo = tipo === valor;
              return (
                <button
                  key={valor}
                  type="button"
                  role="tab"
                  aria-selected={activo}
                  onClick={() => cambiarTipo(valor)}
                  className={cn(
                    "flex h-9 flex-1 items-center justify-center gap-1.5 rounded-md text-sm font-semibold transition-colors",
                    !activo && "text-ink-3",
                    activo && valor === "gasto" && "bg-critical/15 text-critical",
                    activo && valor === "ingreso" && "bg-good/15 text-good-text",
                  )}
                >
                  <Icono size={15} aria-hidden />
                  {etiqueta}
                </button>
              );
            })}
          </div>

          {/* Monto protagonista, teñido según el tipo */}
          <div className="mt-4 flex items-baseline justify-center gap-1 sm:mt-5">
            <span
              className={cn(
                "text-xl sm:text-2xl",
                esGasto ? "text-critical/70" : "text-good-text/70",
              )}
            >
              {esGasto ? "−" : "+"} S/
            </span>
            <input
              ref={montoRef}
              autoFocus
              inputMode="decimal"
              value={monto}
              onChange={(e) => setMonto(e.target.value.replace(",", ".").replace(/[^\d.]/g, ""))}
              placeholder="0.00"
              aria-label="Monto"
              className={cn(
                "w-36 bg-transparent text-center text-[2.5rem] font-semibold leading-none tracking-tight outline-none placeholder:text-ink-3/40 sm:w-40 sm:text-5xl",
                esGasto ? "text-critical" : "text-good-text",
              )}
            />
          </div>
        </div>

        {/* ── Cuerpo scrolleable ── */}
        <div className="min-h-0 flex-1 overflow-y-auto px-4 pt-4 sm:px-6 sm:pt-5">
          <p className="text-center text-[15px] leading-[2.6rem] text-ink-2 sm:text-[17px] sm:leading-[2.9rem]">
            {esGasto ? "Gasté en " : "Recibí de "}
            <Slot>
              <Select
                valor={categoria}
                onChange={setCategoria}
                opciones={categorias}
                aria-label="Categoría"
              />
            </Slot>{" "}
            {esGasto ? "pagando con " : "en "}
            <Slot>
              <Select
                valor={String(cuentaId ?? "")}
                onChange={(v) => setCuentaId(Number(v))}
                opciones={cuentasOpts}
                aria-label="Cuenta"
              />
            </Slot>{" "}
            el{" "}
            <Slot>
              <input
                type="date"
                value={fecha}
                max={hoyISO()}
                onChange={(e) => e.target.value && setFecha(e.target.value)}
                aria-label="Fecha"
                className="bg-transparent text-sm font-medium text-ink outline-none [color-scheme:inherit] sm:text-[15px]"
              />
            </Slot>
          </p>

          <div className="mt-1 flex justify-center gap-1.5">
            {[
              { etiqueta: "Hoy", valor: hoyISO() },
              { etiqueta: "Ayer", valor: desplazarDias(-1) },
              { etiqueta: "Anteayer", valor: desplazarDias(-2) },
            ].map((d) => (
              <button
                key={d.etiqueta}
                type="button"
                onClick={() => setFecha(d.valor)}
                className={cn(
                  "h-8 rounded-lg px-2.5 text-xs font-medium transition-colors",
                  fecha === d.valor
                    ? "bg-accent/15 text-accent"
                    : "text-ink-3 hover:bg-page hover:text-ink-2",
                )}
              >
                {d.etiqueta}
              </button>
            ))}
          </div>

          <input
            value={nota}
            onChange={(e) => setNota(e.target.value)}
            placeholder={esGasto ? "¿En qué? (opcional)" : "¿De quién? (opcional)"}
            maxLength={300}
            className="mt-4 h-11 w-full rounded-xl bg-page px-3.5 text-sm text-ink ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
          />

          {crear.isError && (
            <p role="alert" className="mt-3 text-center text-sm text-critical">
              No se pudo registrar. Intenta de nuevo.
            </p>
          )}
        </div>

        {/* ── Acciones fijas: siempre visibles sobre el teclado ── */}
        <div className="shrink-0 border-t border-hairline px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:px-6 sm:py-4 sm:pb-4">
          <div className="flex gap-3">
            <Boton type="button" variante="secundario" className="flex-1" onClick={cerrar}>
              Cancelar
            </Boton>
            <Boton type="submit" className="flex-[2]" disabled={!montoValido || crear.isPending}>
              {crear.isPending ? "Guardando…" : esGasto ? "Registrar gasto" : "Registrar ingreso"}
            </Boton>
          </div>
        </div>
      </form>
    </div>
  );
}

function Slot({ children }: { children: React.ReactNode }) {
  return <span className="slot">{children}</span>;
}

type Opcion = { valor: string; etiqueta: string };

/** Select nativo (picker del sistema en móvil) presentado como palabra de la frase. */
function Select({
  valor,
  onChange,
  opciones,
  ...props
}: {
  valor: string;
  onChange: (v: string) => void;
  opciones: readonly string[] | Opcion[];
} & Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "value" | "onChange">) {
  const items: Opcion[] = opciones.map((o) =>
    typeof o === "string" ? { valor: o, etiqueta: o } : o,
  );
  return (
    <span className="relative inline-flex items-center pr-4">
      <select
        {...props}
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-transparent text-sm font-medium text-ink outline-none sm:text-[15px]"
      >
        {items.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.etiqueta}
          </option>
        ))}
      </select>
      <ChevronDown
        size={14}
        aria-hidden
        className="pointer-events-none absolute right-0 text-ink-3"
      />
    </span>
  );
}

function hoyISO(): string {
  return new Date().toLocaleDateString("sv-SE"); // sv-SE => YYYY-MM-DD en hora local
}

function desplazarDias(dias: number): string {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  return d.toLocaleDateString("sv-SE");
}
