import { ArrowDownLeft, ArrowUpRight, Calendar, Check, Pencil, Plus, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { useCategorias, useCrearMovimiento, useCuentas } from "@/api/queries";
import { CATEGORIAS, CATEGORIAS_INGRESO } from "@/api/types";
import { cn } from "@/lib/cn";
import { iconoCategoria } from "@/lib/iconos";
import { money } from "@/lib/money";
import { useUiStore, type TipoMovimiento } from "@/stores/uiStore";

/** Captura por pasos: 4 respuestas y listo. Bottom sheet en móvil, diálogo en escritorio.
 *  Cabecera y acciones fijas para que el teclado virtual nunca tape el monto ni el botón. */
export function CapturaRapida() {
  const tipoInicial = useUiStore((s) => s.captura);
  const cerrar = useUiStore((s) => s.cerrarCaptura);
  const { data: cuentas } = useCuentas();
  const crear = useCrearMovimiento();
  const montoRef = useRef<HTMLInputElement>(null);

  const [tipo, setTipo] = useState<TipoMovimiento>("gasto");
  const [monto, setMonto] = useState("");
  const [categoria, setCategoria] = useState("");
  const [cuentaId, setCuentaId] = useState<number | null>(null);
  const [fecha, setFecha] = useState(hoyISO);
  const [nota, setNota] = useState("");
  const [verFecha, setVerFecha] = useState(false);
  const [verTodasCat, setVerTodasCat] = useState(false);

  const abierto = tipoInicial !== null;

  // El catálogo real vive en la base y lo comparte el bot; las constantes solo
  // cubren el primer render mientras la respuesta llega.
  const { data: catalogo } = useCategorias({ tipo });
  const catsBase = useMemo(
    () =>
      // 'ambos' es Transferencia: tiene su propio flujo, no se registra desde acá
      catalogo?.filter((c) => c.tipo !== "ambos").map((c) => c.nombre) ??
      [...(tipo === "gasto" ? CATEGORIAS : CATEGORIAS_INGRESO)],
    [catalogo, tipo],
  );

  useEffect(() => {
    if (catsBase.length && !catsBase.includes(categoria)) setCategoria(catsBase[0]);
  }, [catsBase, categoria]);

  useEffect(() => {
    if (!abierto) return;
    setTipo(tipoInicial);
    setCategoria("");
    setMonto("");
    setNota("");
    setFecha(hoyISO());
    setVerFecha(false);
    setVerTodasCat(false);
    crear.reset();
    // crear.reset es estable; solo interesa reaccionar a la apertura
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto, tipoInicial]);

  useEffect(() => {
    if (cuentas?.length && cuentaId === null) {
      setCuentaId((cuentas.find((c) => c.es_principal) ?? cuentas[0]).id);
    }
  }, [cuentas, cuentaId]);

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

  if (!abierto) return null;

  const esGasto = tipo === "gasto";
  const cats = verTodasCat ? catsBase : catsBase.slice(0, 7);
  const montoValido = Number(monto) > 0;

  function cambiarTipo(nuevo: TipoMovimiento) {
    setTipo(nuevo);
    setCategoria(""); // el efecto elige la primera del catálogo del nuevo tipo
    montoRef.current?.focus();
  }

  function enviar() {
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
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/45 backdrop-blur-[2px] sm:items-center sm:p-4"
      onClick={cerrar}
    >
      <form
        role="dialog"
        aria-label={esGasto ? "Registrar gasto" : "Registrar ingreso"}
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          enviar();
        }}
        className="flex max-h-[94dvh] w-full max-w-[34rem] flex-col rounded-t-2xl bg-card shadow-2xl sm:max-h-[90dvh] sm:rounded-2xl"
      >
        {/* ── Cabecera ── */}
        <div className="shrink-0 px-5 pt-4 sm:px-6 sm:pt-6">
          <div aria-hidden className="mx-auto mb-3 h-1 w-9 rounded-full bg-hairline sm:hidden" />
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <h2 className="text-xl font-bold tracking-tight">Nuevo movimiento</h2>
              <p className="mt-0.5 text-sm text-ink-2">
                <span className="hidden sm:inline">
                  Respondé de arriba hacia abajo, sin salir del teclado
                </span>
                <span className="sm:hidden">4 respuestas y listo</span>
              </p>
            </div>
            <button
              type="button"
              onClick={cerrar}
              aria-label="Cerrar"
              className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-card-soft text-ink-2 transition-colors hover:text-ink"
            >
              <X size={18} />
            </button>
          </div>

          {/* Segmento Gasto / Ingreso */}
          <div
            role="tablist"
            aria-label="Tipo de movimiento"
            className="mt-4 flex rounded-xl bg-card-soft p-1"
          >
            {(
              [
                { valor: "gasto", etiqueta: "Gasto", Icono: ArrowUpRight, color: "text-bad" },
                { valor: "ingreso", etiqueta: "Ingreso", Icono: ArrowDownLeft, color: "text-good-ink" },
              ] as const
            ).map(({ valor, etiqueta, Icono, color }) => {
              const activo = tipo === valor;
              return (
                <button
                  key={valor}
                  type="button"
                  role="tab"
                  aria-selected={activo}
                  onClick={() => cambiarTipo(valor)}
                  className={cn(
                    "flex h-11 flex-1 items-center justify-center gap-2 rounded-lg text-[15px] font-semibold transition-colors",
                    activo
                      ? "bg-card text-ink shadow-sm ring-1 ring-[var(--ring)]"
                      : "text-ink-2",
                  )}
                >
                  <Icono size={16} className={activo ? color : undefined} aria-hidden />
                  {etiqueta}
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Cuerpo scrolleable ── */}
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-6">
          <Paso n={1} pregunta={esGasto ? "¿Cuánto gastaste?" : "¿Cuánto recibiste?"}>
            <div
              className={cn(
                "flex items-center gap-2 rounded-xl bg-card-soft px-4 transition-shadow",
                "ring-2",
                montoValido ? "ring-accent" : "ring-transparent",
              )}
            >
              <span className="text-2xl font-semibold text-ink-3">$</span>
              <input
                ref={montoRef}
                autoFocus
                inputMode="decimal"
                value={monto}
                onChange={(e) =>
                  setMonto(e.target.value.replace(",", ".").replace(/[^\d.]/g, ""))
                }
                placeholder="0.00"
                aria-label="Monto"
                className="h-[4.25rem] min-w-0 flex-1 bg-transparent text-[2.25rem] font-bold tracking-tight outline-none placeholder:text-ink-3/50 tnum"
              />
              <span className="text-sm font-medium text-ink-3">PEN</span>
            </div>
          </Paso>

          <Paso n={2} pregunta="¿En qué categoría?">
            <div className="flex flex-wrap gap-2">
              {cats.map((c) => {
                const Icono = iconoCategoria(c);
                return (
                  <Chip key={c} activo={categoria === c} onClick={() => setCategoria(c)}>
                    <Icono size={15} aria-hidden />
                    {c}
                  </Chip>
                );
              })}
              {!verTodasCat && catsBase.length > 7 && (
                <Chip activo={false} onClick={() => setVerTodasCat(true)}>
                  <Plus size={15} aria-hidden />
                  Otra
                </Chip>
              )}
            </div>
          </Paso>

          <Paso n={3} pregunta={esGasto ? "¿Desde qué cuenta?" : "¿En qué cuenta?"}>
            <div className="flex flex-wrap gap-2">
              {(cuentas ?? []).map((c) => (
                <Chip key={c.id} activo={cuentaId === c.id} onClick={() => setCuentaId(c.id)}>
                  {c.nombre}
                </Chip>
              ))}
            </div>
          </Paso>

          <Paso n={4} pregunta="¿Cuándo fue?">
            <div className="flex flex-wrap gap-2">
              {[
                { etiqueta: "Hoy", valor: hoyISO() },
                { etiqueta: "Ayer", valor: desplazarDias(-1) },
                { etiqueta: "Anteayer", valor: desplazarDias(-2) },
              ].map((d) => (
                <Chip
                  key={d.etiqueta}
                  activo={!verFecha && fecha === d.valor}
                  onClick={() => {
                    setFecha(d.valor);
                    setVerFecha(false);
                  }}
                >
                  {d.etiqueta}
                </Chip>
              ))}
              <Chip activo={verFecha} onClick={() => setVerFecha(true)}>
                <Calendar size={15} aria-hidden />
                <span className="hidden sm:inline">Elegir fecha</span>
                <span className="sm:hidden">Fecha</span>
              </Chip>
            </div>
            {verFecha && (
              <input
                type="date"
                value={fecha}
                max={hoyISO()}
                onChange={(e) => e.target.value && setFecha(e.target.value)}
                aria-label="Fecha"
                className="mt-2 h-11 w-full rounded-xl bg-card-soft px-3 text-sm outline-none [color-scheme:inherit] focus:ring-2 focus:ring-accent"
              />
            )}
          </Paso>

          <div className="mt-5 flex items-center gap-2 rounded-xl bg-card-soft px-3.5">
            <Pencil size={15} className="shrink-0 text-ink-3" aria-hidden />
            <input
              value={nota}
              onChange={(e) => setNota(e.target.value)}
              placeholder={
                esGasto ? "Nota (opcional) — ej. compra semanal" : "Nota (opcional) — ej. sueldo"
              }
              maxLength={300}
              className="h-12 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-ink-3"
            />
          </div>

          {crear.isError && (
            <p role="alert" className="mt-3 text-sm font-medium text-bad-ink">
              No se pudo registrar. Intentá de nuevo.
            </p>
          )}
        </div>

        {/* ── Acciones fijas ── */}
        <div className="shrink-0 border-t border-hairline px-5 py-3.5 pb-[calc(0.875rem+env(safe-area-inset-bottom))] sm:px-6 sm:py-4 sm:pb-4">
          {/* Escritorio: atajos + Cancelar + Guardar */}
          <div className="hidden items-center gap-3 sm:flex">
            <p className="text-xs text-ink-3">Enter para guardar · Esc para cancelar</p>
            <button
              type="button"
              onClick={cerrar}
              className="ml-auto h-11 rounded-xl bg-card px-5 text-sm font-semibold text-ink shadow-sm ring-1 ring-[var(--ring)] transition-colors hover:bg-card-soft"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={!montoValido || crear.isPending}
              className="inline-flex h-11 items-center gap-2 rounded-xl bg-accent px-5 text-sm font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
            >
              <Check size={17} />
              {crear.isPending ? "Guardando…" : esGasto ? "Guardar gasto" : "Guardar ingreso"}
            </button>
          </div>

          {/* Móvil: un solo botón ancho con el monto */}
          <button
            type="submit"
            disabled={!montoValido || crear.isPending}
            className="inline-flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-accent text-[15px] font-semibold text-white transition-colors disabled:opacity-50 sm:hidden"
          >
            <Check size={18} />
            {crear.isPending
              ? "Guardando…"
              : montoValido
                ? `Guardar ${esGasto ? "gasto" : "ingreso"} de ${money(Number(monto))}`
                : `Guardar ${esGasto ? "gasto" : "ingreso"}`}
          </button>
        </div>
      </form>
    </div>
  );
}

/** Bloque de pregunta con su número en círculo, como el mockup. */
function Paso({
  n,
  pregunta,
  children,
}: {
  n: number;
  pregunta: string;
  children: React.ReactNode;
}) {
  return (
    <div className={n === 1 ? "" : "mt-5"}>
      <div className="mb-2 flex items-center gap-2">
        <span className="flex size-5 items-center justify-center rounded-full bg-accent-soft text-[11px] font-bold text-accent-ink">
          {n}
        </span>
        <span className="text-sm font-semibold">{pregunta}</span>
      </div>
      {children}
    </div>
  );
}

function Chip({
  activo,
  onClick,
  children,
}: {
  activo: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={activo}
      className={cn(
        "inline-flex h-11 items-center gap-1.5 rounded-full px-4 text-sm font-medium transition-colors",
        activo
          ? "bg-accent-soft text-accent-ink ring-1 ring-accent/40"
          : "bg-card-soft text-ink-2 hover:text-ink",
      )}
    >
      {children}
    </button>
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
