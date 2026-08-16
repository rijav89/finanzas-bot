import { Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { useCategorias, useGuardarPresupuestos, usePresupuestos } from "@/api/queries";
import { BarraProgreso } from "@/components/ui/BarraProgreso";
import { Boton } from "@/components/ui/Boton";
import { Semaforo } from "@/components/ui/Semaforo";
import { cn } from "@/lib/cn";
import { money } from "@/lib/money";

const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export default function Presupuestos() {
  const hoy = new Date();
  const [anio, setAnio] = useState(hoy.getFullYear());
  const [mes, setMes] = useState(hoy.getMonth() + 1);

  const { data, isLoading } = usePresupuestos(anio, mes);
  const { data: categorias } = useCategorias();
  const guardar = useGuardarPresupuestos();

  const [editando, setEditando] = useState(false);
  const [borrador, setBorrador] = useState<Record<string, string>>({});

  useEffect(() => {
    if (data && !editando) {
      setBorrador(
        Object.fromEntries(data.items.map((i) => [i.categoria, String(i.monto_limite)])),
      );
    }
  }, [data, editando]);

  function cambiarMes(delta: number) {
    const d = new Date(anio, mes - 1 + delta, 1);
    setAnio(d.getFullYear());
    setMes(d.getMonth() + 1);
    setEditando(false);
  }

  const disponibles = (categorias ?? [])
    .map((c) => c.nombre)
    .filter((n) => n !== "Transferencia" && !(n in borrador));

  return (
    <div className="mx-auto max-w-3xl pb-8">
      <header className="flex items-center gap-3 py-4">
        <h1 className="text-xl font-semibold">Presupuestos</h1>
        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => cambiarMes(-1)}
            className="flex size-9 items-center justify-center rounded-lg text-ink-2 hover:bg-card"
            aria-label="Mes anterior"
          >
            ‹
          </button>
          <span className="min-w-[8.5rem] text-center text-sm capitalize text-ink-2">
            {MESES[mes - 1]} {anio}
          </span>
          <button
            onClick={() => cambiarMes(1)}
            className="flex size-9 items-center justify-center rounded-lg text-ink-2 hover:bg-card"
            aria-label="Mes siguiente"
          >
            ›
          </button>
        </div>
      </header>

      {isLoading && <div className="h-40 animate-pulse rounded-2xl bg-card" />}

      {data && (
        <>
          <section className="rounded-2xl bg-card p-4 ring-1 ring-[var(--border-ring)] sm:p-5">
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-ink-2">Presupuestado</span>
              <span className="text-lg font-semibold tabular-nums">
                {money(data.total_limite)}
              </span>
            </div>
            <div className="mt-1 flex items-baseline justify-between">
              <span className="text-sm text-ink-2">Gastado</span>
              <span className="text-lg font-semibold tabular-nums">
                {money(data.total_gastado)}
              </span>
            </div>
            {data.total_limite > 0 && (
              <BarraProgreso
                className="mt-3"
                porcentaje={(data.total_gastado / data.total_limite) * 100}
                estado={
                  data.total_gastado > data.total_limite
                    ? "critico"
                    : data.total_gastado / data.total_limite >= 0.8
                      ? "atencion"
                      : "bien"
                }
              />
            )}
          </section>

          <div className="mt-4 flex items-center gap-2">
            <h2 className="text-sm font-medium text-ink-2">Por categoría</h2>
            <div className="ml-auto">
              {editando ? (
                <div className="flex gap-2">
                  <Boton variante="secundario" onClick={() => setEditando(false)}>
                    Cancelar
                  </Boton>
                  <Boton
                    disabled={guardar.isPending}
                    onClick={() =>
                      guardar.mutate(
                        {
                          anio,
                          mes,
                          items: Object.entries(borrador)
                            .filter(([, v]) => Number(v) > 0)
                            .map(([categoria, monto_limite]) => ({ categoria, monto_limite })),
                        },
                        { onSuccess: () => setEditando(false) },
                      )
                    }
                  >
                    <Save size={16} className="mr-1.5 inline" />
                    {guardar.isPending ? "Guardando…" : "Guardar"}
                  </Boton>
                </div>
              ) : (
                <Boton variante="secundario" onClick={() => setEditando(true)}>
                  Editar
                </Boton>
              )}
            </div>
          </div>

          {editando ? (
            <section className="mt-3 space-y-2">
              {Object.entries(borrador).map(([cat, valor]) => (
                <div
                  key={cat}
                  className="flex items-center gap-3 rounded-xl bg-card p-3 ring-1 ring-[var(--border-ring)]"
                >
                  <span className="flex-1 truncate text-sm">{cat}</span>
                  <span className="text-sm text-ink-3">S/</span>
                  <input
                    inputMode="decimal"
                    value={valor}
                    onChange={(e) =>
                      setBorrador({ ...borrador, [cat]: e.target.value.replace(/[^\d.]/g, "") })
                    }
                    className="h-10 w-24 rounded-lg bg-page px-2 text-right text-sm tabular-nums outline-none ring-1 ring-[var(--border-ring)] focus:ring-2 focus:ring-accent"
                  />
                  <button
                    onClick={() => {
                      const { [cat]: _, ...resto } = borrador;
                      setBorrador(resto);
                    }}
                    aria-label={`Quitar ${cat}`}
                    className="flex size-10 items-center justify-center rounded-lg text-ink-3 hover:text-critical"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}

              {disponibles.length > 0 && (
                <label className="flex items-center gap-2 rounded-xl border border-dashed border-hairline p-3 text-sm text-ink-2">
                  <Plus size={16} />
                  Agregar categoría
                  <select
                    value=""
                    onChange={(e) =>
                      e.target.value && setBorrador({ ...borrador, [e.target.value]: "" })
                    }
                    className="ml-auto h-10 rounded-lg bg-page px-2 text-sm outline-none ring-1 ring-[var(--border-ring)]"
                  >
                    <option value="">Elegir…</option>
                    {disponibles.map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </section>
          ) : data.items.length === 0 ? (
            <p className="mt-3 rounded-2xl bg-card p-6 text-center text-sm text-ink-3 ring-1 ring-[var(--border-ring)]">
              Sin presupuestos para {MESES[mes - 1]}. Tocá «Editar» para definirlos.
            </p>
          ) : (
            <section className="mt-3 space-y-2">
              {data.items.map((p) => (
                <article
                  key={p.id}
                  className="rounded-xl bg-card p-3.5 ring-1 ring-[var(--border-ring)]"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="truncate text-sm font-medium">{p.categoria}</span>
                    <span className="shrink-0 text-sm tabular-nums text-ink-2">
                      {money(p.gastado)}{" "}
                      <span className="text-ink-3">/ {money(p.monto_limite)}</span>
                    </span>
                  </div>
                  <BarraProgreso className="mt-2" porcentaje={p.porcentaje} estado={p.semaforo} />
                  <div className="mt-1.5 flex items-center justify-between text-xs">
                    <span className={cn("tabular-nums", p.disponible < 0 && "text-critical")}>
                      {p.disponible < 0
                        ? `Excedido ${money(-p.disponible)}`
                        : `Disponible ${money(p.disponible)}`}
                    </span>
                    <span className="text-ink-3 tabular-nums">{p.porcentaje}%</span>
                  </div>
                </article>
              ))}
            </section>
          )}

          {!editando && data.sin_presupuesto.length > 0 && (
            <section className="mt-6">
              <h2 className="text-sm font-medium text-ink-2">Gastás acá, sin presupuesto</h2>
              <ul className="mt-2 space-y-1.5">
                {data.sin_presupuesto.slice(0, 5).map((s) => (
                  <li
                    key={s.categoria}
                    className="flex items-center justify-between rounded-xl bg-card px-3.5 py-2.5 text-sm ring-1 ring-[var(--border-ring)]"
                  >
                    <span className="truncate">{s.categoria}</span>
                    <span className="tabular-nums text-ink-2">{money(s.gastado)}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.items.some((i) => i.semaforo === "critico") && (
            <div className="mt-4">
              <Semaforo estado="critical" etiqueta="Tenés categorías excedidas este mes" />
            </div>
          )}
        </>
      )}
    </div>
  );
}
