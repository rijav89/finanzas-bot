import { ChevronDown } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { useCrearMovimiento, useCuentas } from "@/api/queries";
import { CATEGORIAS, CATEGORIAS_INGRESO } from "@/api/types";
import { Boton } from "@/components/ui/Boton";
import { cn } from "@/lib/cn";
import { useUiStore, type TipoMovimiento } from "@/stores/uiStore";

/** Captura conversacional "Mad Libs" para gastos e ingresos.
 *  El monto es el protagonista; el resto de la frase se completa con slots
 *  que se leen como palabras subrayadas, no como cajas de formulario. */
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

  // Cerrar con Escape
  useEffect(() => {
    if (!abierto) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && cerrar();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
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

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4"
      onClick={cerrar}
    >
      <form
        role="dialog"
        aria-label={tipo === "gasto" ? "Registrar gasto" : "Registrar ingreso"}
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
        className="w-full max-w-lg rounded-t-3xl bg-card p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-2xl ring-1 ring-[var(--border-ring)] sm:rounded-3xl sm:p-6 sm:pb-6"
      >
        {/* Tipo — igual que el bot: Gasto / Ingreso */}
        <div
          role="tablist"
          aria-label="Tipo de movimiento"
          className="mx-auto flex w-full max-w-xs rounded-xl bg-page p-1"
        >
          {(["gasto", "ingreso"] as const).map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={tipo === t}
              onClick={() => cambiarTipo(t)}
              className={cn(
                "h-10 flex-1 rounded-lg text-sm font-medium capitalize transition-colors",
                tipo === t ? "bg-card text-ink shadow-sm" : "text-ink-3 hover:text-ink-2",
              )}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Monto protagonista */}
        <div className="mt-6 flex items-baseline justify-center gap-1.5">
          <span className="text-2xl text-ink-3">S/</span>
          <input
            ref={montoRef}
            autoFocus
            inputMode="decimal"
            value={monto}
            onChange={(e) => setMonto(e.target.value.replace(",", ".").replace(/[^\d.]/g, ""))}
            placeholder="0.00"
            aria-label="Monto"
            className="w-44 bg-transparent text-center text-5xl font-semibold tracking-tight text-ink outline-none placeholder:text-ink-3/40"
          />
        </div>

        {/* Frase Mad Libs */}
        <p className="mt-6 text-center text-lg leading-[3.25rem] text-ink-2">
          {tipo === "gasto" ? "Gasté en " : "Recibí de "}
          <Slot>
            <Select
              valor={categoria}
              onChange={setCategoria}
              opciones={categorias}
              aria-label="Categoría"
            />
          </Slot>{" "}
          {tipo === "gasto" ? "pagando con " : "en "}
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
              className="bg-transparent text-base text-ink outline-none [color-scheme:inherit]"
            />
          </Slot>
        </p>

        {/* Atajos de fecha */}
        <div className="mt-2 flex justify-center gap-2">
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
                "h-9 rounded-lg px-3 text-xs font-medium transition-colors",
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
          placeholder={tipo === "gasto" ? "¿En qué? (opcional)" : "¿De quién? (opcional)"}
          maxLength={300}
          className="mt-5 h-11 w-full rounded-xl bg-page px-3.5 text-sm text-ink ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
        />

        {crear.isError && (
          <p role="alert" className="mt-3 text-center text-sm text-critical">
            No se pudo registrar. Intenta de nuevo.
          </p>
        )}

        <div className="mt-5 flex gap-3">
          <Boton type="button" variante="secundario" className="flex-1" onClick={cerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" className="flex-[2]" disabled={!montoValido || crear.isPending}>
            {crear.isPending
              ? "Guardando…"
              : tipo === "gasto"
                ? "Registrar gasto"
                : "Registrar ingreso"}
          </Boton>
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
    <span className="relative inline-flex items-center pr-5">
      <select
        {...props}
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-transparent text-base font-medium text-ink outline-none"
      >
        {items.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.etiqueta}
          </option>
        ))}
      </select>
      <ChevronDown
        size={15}
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
