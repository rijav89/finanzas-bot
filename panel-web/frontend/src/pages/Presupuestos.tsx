import { ChevronLeft, ChevronRight, Plus, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { useCategorias, useGuardarPresupuestos, usePresupuestos } from "@/api/queries";
import type { Semaforo } from "@/api/types";
import { HeaderMovil } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { BarraProgreso, type TonoBarra } from "@/components/ui/BarraProgreso";
import { Boton } from "@/components/ui/Boton";
import { Card, PageHeader } from "@/components/ui/Card";
import { iconoCategoria } from "@/lib/iconos";
import { money } from "@/lib/money";

const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

const TONO: Record<Semaforo, TonoBarra> = {
  bien: "good",
  atencion: "warn",
  critico: "bad",
  info: "accent",
};
const TONO_BADGE = { bien: "good", atencion: "warn", critico: "bad", info: "neutro" } as const;

export default function Presupuestos() {
  const hoy = new Date();
  const [anio, setAnio] = useState(hoy.getFullYear());
  const [mes, setMes] = useState(hoy.getMonth() + 1);

  const { data, isPending } = usePresupuestos(anio, mes);
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

  const consumido = data && data.total_limite > 0
    ? (data.total_gastado / data.total_limite) * 100
    : 0;
  const tonoTotal: Semaforo =
    consumido > 100 ? "critico" : consumido >= 80 ? "atencion" : "bien";

  return (
    <>
      <HeaderMovil titulo="Presupuestos" subtitulo={`Topes · ${MESES[mes - 1]}`} />
      <div className="hidden lg:block">
        <PageHeader
          titulo="Presupuestos"
          subtitulo={`Topes por categoría · ${MESES[mes - 1]} ${anio}`}
          acciones={
            editando ? (
              <>
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
                  <Save size={17} />
                  {guardar.isPending ? "Guardando…" : "Guardar"}
                </Boton>
              </>
            ) : (
              <Boton onClick={() => setEditando(true)}>
                <Plus size={18} />
                Nuevo tope
              </Boton>
            )
          }
        />
      </div>

      {/* Selector de mes */}
      <div className="flex flex-wrap items-center gap-3 pb-4">
        <div className="flex items-center gap-1 rounded-xl bg-card p-1 shadow-sm ring-1 ring-[var(--ring)]">
          <button
            onClick={() => cambiarMes(-1)}
            aria-label="Mes anterior"
            className="flex size-9 items-center justify-center rounded-lg text-ink-2 hover:bg-card-soft"
          >
            <ChevronLeft size={18} />
          </button>
          <span className="min-w-[8.5rem] text-center text-sm font-semibold capitalize">
            {MESES[mes - 1]} {anio}
          </span>
          <button
            onClick={() => cambiarMes(1)}
            aria-label="Mes siguiente"
            className="flex size-9 items-center justify-center rounded-lg text-ink-2 hover:bg-card-soft"
          >
            <ChevronRight size={18} />
          </button>
        </div>
        <p className="hidden text-sm text-ink-3 lg:ml-auto lg:block">
          El semáforo se calcula sobre lo que llevás gastado del tope
        </p>
        <div className="ml-auto lg:hidden">
          <Boton variante="secundario" onClick={() => setEditando((v) => !v)}>
            {editando ? "Cancelar" : "Editar"}
          </Boton>
        </div>
      </div>

      {isPending && <div className="h-32 animate-pulse rounded-2xl bg-card" />}

      {data && (
        <>
          {/* Resumen del mes */}
          <Card className="mb-4">
            <h2 className="font-semibold text-ink-2">Presupuesto del mes</h2>
            <div className="mt-3 flex flex-wrap items-end gap-x-10 gap-y-4">
              <Metrica etiqueta="Tope total" valor={money(data.total_limite)} />
              <Metrica
                etiqueta="Gastado"
                valor={money(data.total_gastado)}
                clase="text-bad-ink"
              />
              <Metrica
                etiqueta="Te queda"
                valor={money(data.total_limite - data.total_gastado)}
                clase={
                  data.total_limite - data.total_gastado < 0 ? "text-bad-ink" : "text-good-ink"
                }
              />
              <div className="min-w-[14rem] flex-1">
                <div className="mb-2 flex items-center justify-end gap-2">
                  <span className="text-sm text-ink-2 tnum">
                    {Math.round(consumido)}% del tope consumido
                  </span>
                  <Badge tono={TONO_BADGE[tonoTotal]}>
                    {tonoTotal === "critico"
                      ? "Excedido"
                      : tonoTotal === "atencion"
                        ? "Cuidado"
                        : "En orden"}
                  </Badge>
                </div>
                <BarraProgreso porcentaje={consumido} tono={TONO[tonoTotal]} />
              </div>
            </div>
          </Card>

          <div className="grid gap-4 lg:grid-cols-3">
            {/* Por categoría */}
            <Card className="lg:col-span-2">
              <h2 className="font-semibold text-ink-2">Por categoría</h2>

              {editando ? (
                <div className="mt-4 space-y-2">
                  {Object.entries(borrador).map(([cat, valor]) => (
                    <div key={cat} className="flex items-center gap-3 rounded-xl bg-card-soft p-3">
                      <span className="min-w-0 flex-1 truncate text-sm font-medium">{cat}</span>
                      <span className="text-sm text-ink-3">$</span>
                      <input
                        inputMode="decimal"
                        value={valor}
                        onChange={(e) =>
                          setBorrador({
                            ...borrador,
                            [cat]: e.target.value.replace(/[^\d.]/g, ""),
                          })
                        }
                        className="h-10 w-24 rounded-lg bg-card px-2 text-right text-sm outline-none ring-1 ring-[var(--ring)] focus:ring-2 focus:ring-accent tnum"
                      />
                      <button
                        onClick={() => {
                          const { [cat]: _, ...resto } = borrador;
                          setBorrador(resto);
                        }}
                        aria-label={`Quitar ${cat}`}
                        className="flex size-9 items-center justify-center rounded-lg text-ink-3 hover:text-bad"
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
                        className="ml-auto h-10 rounded-lg bg-card-soft px-2 text-sm outline-none"
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

                  <div className="pt-2 lg:hidden">
                    <Boton
                      className="w-full"
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
                      <Save size={17} />
                      Guardar topes
                    </Boton>
                  </div>
                </div>
              ) : data.items.length === 0 ? (
                <p className="py-10 text-center text-sm text-ink-3">
                  Sin topes para {MESES[mes - 1]}. Tocá «Nuevo tope» para definirlos.
                </p>
              ) : (
                <ul className="mt-4 space-y-5">
                  {data.items.map((p) => (
                    <li key={p.id}>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        <span className="font-semibold">{p.categoria}</span>
                        <Badge tono={TONO_BADGE[p.semaforo]}>{Math.round(p.porcentaje)}%</Badge>
                        <span className="ml-auto text-sm text-ink-2 tnum">
                          <span className="font-semibold text-ink">{money(p.gastado)}</span> de{" "}
                          {money(p.monto_limite)}
                        </span>
                      </div>
                      <BarraProgreso
                        className="mt-2"
                        porcentaje={p.porcentaje}
                        tono={TONO[p.semaforo]}
                      />
                      <p
                        className={`mt-1.5 text-sm tnum ${
                          p.disponible < 0 ? "text-bad-ink" : "text-ink-3"
                        }`}
                      >
                        {p.disponible < 0
                          ? `Te pasaste ${money(-p.disponible)}`
                          : `Te queda ${money(p.disponible)}`}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            {/* Sin tope definido */}
            <Card>
              <h2 className="font-semibold text-ink-2">Sin tope definido</h2>
              {data.sin_presupuesto.length === 0 ? (
                <p className="mt-4 text-sm text-ink-3">
                  Todas tus categorías con gasto tienen tope.
                </p>
              ) : (
                <>
                  <p className="mt-2 text-sm text-ink-2">
                    Gastás seguido en estas categorías y todavía no les pusiste un límite.
                  </p>
                  <ul className="mt-4 space-y-1">
                    {data.sin_presupuesto.slice(0, 6).map((s) => {
                      const Icono = iconoCategoria(s.categoria);
                      return (
                        <li
                          key={s.categoria}
                          className="flex items-center gap-3 border-b border-hairline py-3 last:border-0"
                        >
                          <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-card-soft text-ink-2">
                            <Icono size={17} />
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="truncate font-semibold">{s.categoria}</p>
                            <p className="text-sm text-ink-3 tnum">
                              {money(s.gastado)} este mes
                            </p>
                          </div>
                          <button
                            onClick={() => {
                              setEditando(true);
                              setBorrador((b) => ({ ...b, [s.categoria]: "" }));
                            }}
                            className="inline-flex h-9 shrink-0 items-center gap-1 rounded-lg bg-accent-soft px-3 text-sm font-semibold text-accent-ink"
                          >
                            <Plus size={15} />
                            Tope
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </>
              )}
            </Card>
          </div>
        </>
      )}
    </>
  );
}

function Metrica({
  etiqueta,
  valor,
  clase,
}: {
  etiqueta: string;
  valor: string;
  clase?: string;
}) {
  return (
    <div>
      <p className="text-sm text-ink-2">{etiqueta}</p>
      <p className={`mt-1 text-[1.75rem] font-bold leading-none tracking-tight tnum ${clase ?? ""}`}>
        {valor}
      </p>
    </div>
  );
}
