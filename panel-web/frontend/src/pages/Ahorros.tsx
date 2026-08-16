import { PiggyBank, Target } from "lucide-react";
import { useState } from "react";

import { useAhorros, useCuentas, useDefinirMetaAhorro } from "@/api/queries";
import { BarraProgreso } from "@/components/ui/BarraProgreso";
import { Boton } from "@/components/ui/Boton";
import { Semaforo } from "@/components/ui/Semaforo";
import { money } from "@/lib/money";

export default function Ahorros() {
  const { data, isLoading } = useAhorros();
  const { data: cuentas } = useCuentas();
  const [editando, setEditando] = useState<number | null>(null);

  // Cuentas corrientes que aún no son de ahorro: candidatas a convertir
  const candidatas = (cuentas ?? []).filter(
    (c) => !(data?.items ?? []).some((a) => a.cuenta_id === c.id),
  );

  return (
    <div className="mx-auto max-w-3xl pb-8">
      <header className="flex items-center gap-3 py-4">
        <h1 className="text-xl font-semibold">Ahorros</h1>
      </header>

      {isLoading && <div className="h-32 animate-pulse rounded-2xl bg-card" />}

      {data && (
        <>
          <section className="rounded-2xl bg-card p-4 ring-1 ring-[var(--border-ring)] sm:p-5">
            <p className="text-sm text-ink-2">Total ahorrado</p>
            <p className="mt-1 text-3xl font-semibold tabular-nums">
              {money(data.total_ahorrado)}
            </p>
          </section>

          {data.items.length === 0 ? (
            <div className="mt-4 rounded-2xl bg-card p-6 text-center ring-1 ring-[var(--border-ring)]">
              <PiggyBank size={28} className="mx-auto text-ink-3" />
              <p className="mt-3 text-sm text-ink-2">Todavía no tenés cuentas de ahorro.</p>
              <p className="mt-1 text-xs text-ink-3">
                Convertí una cuenta existente asignándole una meta.
              </p>
            </div>
          ) : (
            <section className="mt-4 space-y-2">
              {data.items.map((a) => (
                <article
                  key={a.cuenta_id}
                  className="rounded-xl bg-card p-4 ring-1 ring-[var(--border-ring)]"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="truncate font-medium">{a.nombre}</span>
                    <span className="shrink-0 text-lg font-semibold tabular-nums">
                      {money(a.saldo)}
                    </span>
                  </div>

                  {a.meta ? (
                    <>
                      <BarraProgreso
                        className="mt-2.5"
                        porcentaje={a.meta.porcentaje}
                        estado={a.meta.cumplida ? "bien" : "info"}
                      />
                      <div className="mt-1.5 flex items-center justify-between text-xs">
                        <span className="text-ink-3">
                          Meta {money(a.meta.monto_objetivo)}
                          {a.meta.fecha_objetivo && ` · ${a.meta.fecha_objetivo}`}
                        </span>
                        <span className="tabular-nums text-ink-2">{a.meta.porcentaje}%</span>
                      </div>
                      {a.meta.cumplida ? (
                        <div className="mt-2">
                          <Semaforo estado="good" etiqueta="Meta alcanzada" />
                        </div>
                      ) : (
                        <p className="mt-2 text-xs text-ink-3">
                          Faltan {money(a.meta.falta ?? 0)}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="mt-2 text-xs text-ink-3">Sin meta definida</p>
                  )}

                  <button
                    onClick={() => setEditando(a.cuenta_id)}
                    className="mt-3 text-xs font-medium text-accent"
                  >
                    {a.meta ? "Cambiar meta" : "Definir meta"}
                  </button>
                </article>
              ))}
            </section>
          )}

          {candidatas.length > 0 && (
            <section className="mt-6">
              <h2 className="text-sm font-medium text-ink-2">Convertir en cuenta de ahorro</h2>
              <ul className="mt-2 space-y-1.5">
                {candidatas.map((c) => (
                  <li
                    key={c.id}
                    className="flex items-center gap-3 rounded-xl bg-card px-3.5 py-2.5 ring-1 ring-[var(--border-ring)]"
                  >
                    <Target size={16} className="shrink-0 text-ink-3" />
                    <span className="truncate text-sm">{c.nombre}</span>
                    <button
                      onClick={() => setEditando(c.id)}
                      className="ml-auto shrink-0 text-xs font-medium text-accent"
                    >
                      Asignar meta
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      {editando !== null && (
        <FormMeta cuentaId={editando} onCerrar={() => setEditando(null)} />
      )}
    </div>
  );
}

function FormMeta({ cuentaId, onCerrar }: { cuentaId: number; onCerrar: () => void }) {
  const definir = useDefinirMetaAhorro();
  const [monto, setMonto] = useState("");
  const [fecha, setFecha] = useState("");

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4"
      onClick={onCerrar}
    >
      <form
        role="dialog"
        aria-label="Definir meta de ahorro"
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          if (!(Number(monto) > 0)) return;
          definir.mutate(
            {
              cuentaId,
              monto_objetivo: monto,
              ...(fecha ? { fecha_objetivo: fecha } : {}),
            },
            { onSuccess: onCerrar },
          );
        }}
        className="w-full max-w-md rounded-t-2xl bg-card p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-2xl ring-1 ring-[var(--border-ring)] sm:rounded-2xl sm:pb-5"
      >
        <h2 className="font-semibold">Meta de ahorro</h2>

        <label className="mt-4 block">
          <span className="mb-1 block text-xs text-ink-2">¿Cuánto querés juntar?</span>
          <div className="flex items-center gap-2 rounded-xl bg-page px-3 ring-1 ring-[var(--border-ring)] focus-within:ring-2 focus-within:ring-accent">
            <span className="text-ink-3">S/</span>
            <input
              autoFocus
              inputMode="decimal"
              value={monto}
              onChange={(e) => setMonto(e.target.value.replace(/[^\d.]/g, ""))}
              placeholder="0.00"
              className="h-11 flex-1 bg-transparent text-lg font-semibold tabular-nums outline-none"
            />
          </div>
        </label>

        <label className="mt-3 block">
          <span className="mb-1 block text-xs text-ink-2">¿Para cuándo? (opcional)</span>
          <input
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
            className="h-11 w-full rounded-xl bg-page px-3 text-sm ring-1 ring-[var(--border-ring)] outline-none [color-scheme:inherit] focus:ring-2 focus:ring-accent"
          />
        </label>

        {definir.isError && (
          <p role="alert" className="mt-3 text-sm text-critical">
            No se pudo guardar la meta.
          </p>
        )}

        <div className="mt-5 flex gap-3">
          <Boton type="button" variante="secundario" className="flex-1" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton
            type="submit"
            className="flex-[2]"
            disabled={!(Number(monto) > 0) || definir.isPending}
          >
            {definir.isPending ? "Guardando…" : "Guardar meta"}
          </Boton>
        </div>
      </form>
    </div>
  );
}
