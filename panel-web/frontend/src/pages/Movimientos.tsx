import { Pencil, Search, SlidersHorizontal, Trash2 } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useEliminarMovimiento, useMovimientos } from "@/api/queries";
import type { Movimiento } from "@/api/types";
import { AccionesHeader } from "@/components/layout/AccionesHeader";
import { HeaderMovil } from "@/components/layout/AppShell";
import { Card, PageHeader } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { IconoTile } from "@/lib/iconos";
import { money } from "@/lib/money";

type Filtro = "todos" | "gasto" | "ingreso";

const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export default function Movimientos() {
  // Permite entrar ya filtrado desde otras pantallas (ej. «Ver todos los ingresos»)
  const [params] = useSearchParams();
  const inicial = params.get("tipo");

  const [q, setQ] = useState("");
  const [filtro, setFiltro] = useState<Filtro>(
    inicial === "gasto" || inicial === "ingreso" ? inicial : "todos",
  );
  const { data, isPending } = useMovimientos({
    q: q || undefined,
    tipo: filtro === "todos" ? undefined : filtro,
  });
  const eliminar = useEliminarMovimiento();

  const items = data?.items ?? [];
  const ingresos = items
    .filter((m) => m.tipo === "ingreso")
    .reduce((s, m) => s + Number(m.monto), 0);
  const gastos = items
    .filter((m) => m.tipo === "gasto")
    .reduce((s, m) => s + Number(m.monto), 0);

  const hoy = new Date();
  const periodo = `${MESES[hoy.getMonth()]} ${hoy.getFullYear()}`;

  return (
    <>
      <HeaderMovil titulo="Movimientos" subtitulo={`${items.length} registros · ${MESES[hoy.getMonth()]}`} />
      <div className="hidden lg:block">
        <PageHeader
          titulo="Movimientos"
          subtitulo={`${items.length} registros · ${periodo}`}
          acciones={<AccionesHeader />}
        />
      </div>

      {/* Barra de búsqueda y filtros */}
      <div className="flex flex-wrap items-center gap-2 pb-4">
        <label className="flex h-12 min-w-0 flex-1 items-center gap-2.5 rounded-xl bg-card px-4 shadow-sm ring-1 ring-[var(--ring)] focus-within:ring-2 focus-within:ring-accent">
          <Search size={18} className="shrink-0 text-ink-3" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Buscar por comercio, categoría o nota…"
            className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-ink-3"
          />
        </label>

        <div className="flex rounded-xl bg-card p-1 shadow-sm ring-1 ring-[var(--ring)]">
          {(
            [
              { v: "todos", l: "Todos" },
              { v: "gasto", l: "Gastos" },
              { v: "ingreso", l: "Ingresos" },
            ] as const
          ).map(({ v, l }) => (
            <button
              key={v}
              onClick={() => setFiltro(v)}
              aria-pressed={filtro === v}
              className={cn(
                "h-10 rounded-lg px-4 text-sm font-semibold transition-colors",
                filtro === v ? "bg-card-soft text-ink" : "text-ink-2 hover:text-ink",
              )}
            >
              {l}
            </button>
          ))}
        </div>

        <button
          aria-label="Filtros"
          className="hidden h-12 items-center gap-2 rounded-xl bg-card px-4 text-sm font-medium text-ink-2 shadow-sm ring-1 ring-[var(--ring)] sm:flex"
        >
          <SlidersHorizontal size={16} />
          Filtros
        </button>
      </div>

      <Card padding="p-0">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1 px-5 py-4">
          <h2 className="font-semibold">Historial</h2>
          <div className="ml-auto flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
            <span className="text-ink-2">
              Ingresos{" "}
              <span className="font-semibold text-good-ink tnum">+{money(ingresos)}</span>
            </span>
            <span className="text-ink-2">
              Gastos <span className="font-semibold text-bad-ink tnum">-{money(gastos)}</span>
            </span>
            <span className="text-ink-2">
              Neto{" "}
              <span className="font-semibold tnum">
                {ingresos - gastos >= 0 ? "+" : ""}
                {money(ingresos - gastos)}
              </span>
            </span>
          </div>
        </div>

        {isPending ? (
          <div className="space-y-2 px-5 pb-5">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-16 animate-pulse rounded-xl bg-card-soft" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <p className="px-5 pb-8 pt-4 text-center text-sm text-ink-3">
            No hay movimientos que coincidan.
          </p>
        ) : (
          <div className="pb-2">
            {agrupar(items).map(([etiqueta, filas]) => (
              <section key={etiqueta}>
                <h3 className="px-5 pb-1 pt-4 text-xs font-semibold uppercase tracking-wide text-ink-3">
                  {etiqueta}
                </h3>
                <ul>
                  {filas.map((m) => (
                    <li key={`${m.tipo}-${m.id}`} className="group px-2">
                      <div className="flex items-center gap-3 rounded-xl px-3 py-3 transition-colors hover:bg-card-soft">
                        <IconoTile categoria={m.categoria} ingreso={m.tipo === "ingreso"} />
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-semibold">
                            {m.descripcion || m.categoria || "Sin descripción"}
                          </p>
                          <p className="mt-0.5 truncate text-sm text-ink-2">{m.categoria}</p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p
                            className={cn(
                              "font-bold tnum",
                              m.tipo === "ingreso" ? "text-good-ink" : "text-ink",
                            )}
                          >
                            {m.tipo === "ingreso" ? "+" : "-"}
                            {money(Number(m.monto))}
                          </p>
                          <p className="mt-0.5 text-xs text-ink-3">{diaCorto(m.fecha)}</p>
                        </div>
                        <div className="flex shrink-0 gap-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
                          <button
                            aria-label="Editar"
                            className="flex size-9 items-center justify-center rounded-lg bg-card text-ink-2 shadow-sm ring-1 ring-[var(--ring)] hover:text-ink"
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            aria-label="Eliminar"
                            onClick={() =>
                              eliminar.mutate({
                                tipo: m.tipo === "gasto" ? "gastos" : "ingresos",
                                id: m.id,
                              })
                            }
                            className="flex size-9 items-center justify-center rounded-lg bg-card text-bad shadow-sm ring-1 ring-[var(--ring)]"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}

/** Agrupa por día con etiquetas relativas (Hoy / Ayer / fecha). */
function agrupar(items: Movimiento[]): [string, Movimiento[]][] {
  const hoy = new Date().toLocaleDateString("sv-SE");
  const ayer = new Date(Date.now() - 86_400_000).toLocaleDateString("sv-SE");
  const grupos = new Map<string, Movimiento[]>();

  for (const m of items) {
    const dia = (m.fecha ?? "").slice(0, 10);
    const etiqueta =
      dia === hoy
        ? `Hoy · ${textoFecha(dia)}`
        : dia === ayer
          ? `Ayer · ${textoFecha(dia)}`
          : textoFecha(dia);
    grupos.set(etiqueta, [...(grupos.get(etiqueta) ?? []), m]);
  }
  return [...grupos.entries()];
}

function textoFecha(iso: string): string {
  if (!iso) return "Sin fecha";
  const [a, m, d] = iso.split("-").map(Number);
  return `${d} de ${MESES[m - 1]}${a !== new Date().getFullYear() ? ` ${a}` : ""}`;
}

function diaCorto(fecha: string | null): string {
  if (!fecha) return "";
  const [, m, d] = fecha.slice(0, 10).split("-").map(Number);
  return `${d} ${MESES[m - 1].slice(0, 3)}`;
}
