import { CalendarClock, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import {
  useCategorias,
  useCrearRecurrente,
  useCuentas,
  useEliminarRecurrente,
  useRecurrentes,
} from "@/api/queries";
import { Boton } from "@/components/ui/Boton";
import { money } from "@/lib/money";

const FRECUENCIAS = [
  { valor: "mensual", etiqueta: "Cada mes" },
  { valor: "semanal", etiqueta: "Cada semana" },
  { valor: "anual", etiqueta: "Cada año" },
] as const;

export default function Recurrentes() {
  const { data, isLoading } = useRecurrentes();
  const eliminar = useEliminarRecurrente();
  const [creando, setCreando] = useState(false);

  return (
    <div className="mx-auto max-w-3xl pb-8">
      <header className="flex items-center gap-3 py-4">
        <h1 className="text-xl font-semibold">Pagos recurrentes</h1>
        <Boton className="ml-auto" onClick={() => setCreando(true)}>
          <Plus size={16} className="mr-1.5 inline" />
          Nuevo
        </Boton>
      </header>

      {isLoading && <div className="h-32 animate-pulse rounded-2xl bg-card" />}

      {data && (
        <>
          <section className="rounded-2xl bg-card p-4 ring-1 ring-[var(--border-ring)] sm:p-5">
            <p className="text-sm text-ink-2">Compromiso mensual</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums">
              {money(data.total_mensual)}
            </p>
            <p className="mt-1 text-xs text-ink-3">
              El bot te avisa el día que vence cada uno.
            </p>
          </section>

          {data.items.length === 0 ? (
            <div className="mt-4 rounded-2xl bg-card p-6 text-center ring-1 ring-[var(--border-ring)]">
              <CalendarClock size={28} className="mx-auto text-ink-3" />
              <p className="mt-3 text-sm text-ink-2">Sin pagos recurrentes.</p>
              <p className="mt-1 text-xs text-ink-3">
                Anotá alquiler, servicios o suscripciones para no olvidarlos.
              </p>
            </div>
          ) : (
            <section className="mt-4 space-y-2">
              {data.items.map((p) => (
                <article
                  key={p.id}
                  className="flex items-center gap-3 rounded-xl bg-card p-3.5 ring-1 ring-[var(--border-ring)]"
                >
                  <div className="flex size-10 shrink-0 flex-col items-center justify-center rounded-lg bg-page">
                    <span className="text-sm font-semibold leading-none tabular-nums">
                      {p.dia_mes}
                    </span>
                    <span className="mt-0.5 text-[9px] uppercase text-ink-3">día</span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{p.descripcion}</p>
                    <p className="mt-0.5 text-xs text-ink-3">
                      {p.categoria}
                      {p.frecuencia !== "mensual" &&
                        ` · ${FRECUENCIAS.find((f) => f.valor === p.frecuencia)?.etiqueta}`}
                    </p>
                  </div>
                  <span className="shrink-0 text-sm font-semibold tabular-nums">
                    {money(p.monto)}
                  </span>
                  <button
                    onClick={() => eliminar.mutate(p.id)}
                    aria-label={`Eliminar ${p.descripcion}`}
                    className="flex size-9 shrink-0 items-center justify-center rounded-lg text-ink-3 hover:text-critical"
                  >
                    <Trash2 size={16} />
                  </button>
                </article>
              ))}
            </section>
          )}
        </>
      )}

      {creando && <FormRecurrente onCerrar={() => setCreando(false)} />}
    </div>
  );
}

function FormRecurrente({ onCerrar }: { onCerrar: () => void }) {
  const { data: cuentas } = useCuentas();
  const { data: categorias } = useCategorias();
  const crear = useCrearRecurrente();

  const [descripcion, setDescripcion] = useState("");
  const [monto, setMonto] = useState("");
  const [dia, setDia] = useState("1");
  const [categoria, setCategoria] = useState("Servicios");
  const [frecuencia, setFrecuencia] = useState<string>("mensual");
  const [cuentaId, setCuentaId] = useState("");

  const diaNum = Number(dia);
  const valido = descripcion.trim() && Number(monto) > 0 && diaNum >= 1 && diaNum <= 31;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4"
      onClick={onCerrar}
    >
      <form
        role="dialog"
        aria-label="Nuevo pago recurrente"
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          if (!valido) return;
          crear.mutate(
            {
              descripcion: descripcion.trim(),
              monto,
              dia_mes: diaNum,
              categoria,
              frecuencia,
              ...(cuentaId ? { cuenta_id: Number(cuentaId) } : {}),
            },
            { onSuccess: onCerrar },
          );
        }}
        className="w-full max-w-md rounded-t-2xl bg-card p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-2xl ring-1 ring-[var(--border-ring)] sm:rounded-2xl sm:pb-5"
      >
        <h2 className="font-semibold">Nuevo pago recurrente</h2>

        <label className="mt-4 block">
          <span className="mb-1 block text-xs text-ink-2">¿Qué pagás?</span>
          <input
            autoFocus
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            placeholder="Alquiler, Netflix, luz…"
            maxLength={200}
            className="h-11 w-full rounded-xl bg-page px-3 text-sm ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
          />
        </label>

        <div className="mt-3 grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1 block text-xs text-ink-2">Monto</span>
            <input
              inputMode="decimal"
              value={monto}
              onChange={(e) => setMonto(e.target.value.replace(/[^\d.]/g, ""))}
              placeholder="0.00"
              className="h-11 w-full rounded-xl bg-page px-3 text-sm tabular-nums ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-ink-2">Día del mes</span>
            <input
              inputMode="numeric"
              value={dia}
              onChange={(e) => setDia(e.target.value.replace(/\D/g, "").slice(0, 2))}
              className="h-11 w-full rounded-xl bg-page px-3 text-sm tabular-nums ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
            />
          </label>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1 block text-xs text-ink-2">Categoría</span>
            <select
              value={categoria}
              onChange={(e) => setCategoria(e.target.value)}
              className="h-11 w-full rounded-xl bg-page px-3 text-sm ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
            >
              {(categorias ?? [])
                .filter((c) => c.nombre !== "Transferencia")
                .map((c) => (
                  <option key={c.id} value={c.nombre}>
                    {c.nombre}
                  </option>
                ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-ink-2">Frecuencia</span>
            <select
              value={frecuencia}
              onChange={(e) => setFrecuencia(e.target.value)}
              className="h-11 w-full rounded-xl bg-page px-3 text-sm ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
            >
              {FRECUENCIAS.map((f) => (
                <option key={f.valor} value={f.valor}>
                  {f.etiqueta}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="mt-3 block">
          <span className="mb-1 block text-xs text-ink-2">Cuenta (opcional)</span>
          <select
            value={cuentaId}
            onChange={(e) => setCuentaId(e.target.value)}
            className="h-11 w-full rounded-xl bg-page px-3 text-sm ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="">Sin especificar</option>
            {(cuentas ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>

        {crear.isError && (
          <p role="alert" className="mt-3 text-sm text-critical">
            No se pudo crear el pago recurrente.
          </p>
        )}

        <div className="mt-5 flex gap-3">
          <Boton type="button" variante="secundario" className="flex-1" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" className="flex-[2]" disabled={!valido || crear.isPending}>
            {crear.isPending ? "Creando…" : "Crear"}
          </Boton>
        </div>
      </form>
    </div>
  );
}
