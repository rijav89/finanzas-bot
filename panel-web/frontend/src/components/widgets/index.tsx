import { AlertTriangle, Check, ChevronDown, ChevronRight, Sparkles, TrendingUp } from "lucide-react";
import { lazy, Suspense, useState } from "react";
import { Link } from "react-router-dom";

import { useInsights, useMarcarInsight } from "@/api/queries";
import type { DashboardResumen, MovimientoReciente, SeveridadInsight } from "@/api/types";
import { BentoCard } from "@/components/bento/BentoCard";
import { Desglose } from "@/components/charts/Desglose";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import { IconoTile } from "@/lib/iconos";
import { money } from "@/lib/money";
import { colorSerie } from "@/lib/series";
import type { WidgetId } from "@/stores/bentoStore";

const LineaSaldo = lazy(() =>
  import("@/components/charts/LineaSaldo").then((m) => ({ default: m.LineaSaldo })),
);
const MiniLinea = lazy(() =>
  import("@/components/charts/LineaSaldo").then((m) => ({ default: m.MiniLinea })),
);

export interface WidgetProps {
  datos: DashboardResumen;
  variante: "compact" | "full";
  className?: string;
}

/** prioridad ≤ 2 se muestra en móvil; el resto vive en escritorio.
 *  El orden es el de lectura de la plata: cuánto tengo, cuánto entró, cuánto salió. */
export const REGISTRO: Record<
  WidgetId,
  { prioridad: number; span: string; Componente: (p: WidgetProps) => JSX.Element }
> = {
  "saldo-total": { prioridad: 1, span: "lg:col-span-2", Componente: SaldoTotal },
  ingresos: { prioridad: 2, span: "lg:col-span-2", Componente: Ingresos },
  gastos: { prioridad: 2, span: "lg:col-span-2", Componente: Gastos },
  "tendencia-saldo": { prioridad: 3, span: "lg:col-span-4", Componente: Tendencia },
  "ultimos-registros": { prioridad: 2, span: "lg:col-span-2", Componente: UltimosRegistros },
  insights: { prioridad: 2, span: "lg:col-span-6", Componente: Insights },
};

/** Variación porcentual contra una referencia, o null si no hay con qué comparar. */
function variacion(actual: number, referencia: number): number | null {
  if (!referencia) return null;
  return ((actual - referencia) / referencia) * 100;
}

function signo(n: number): string {
  return n >= 0 ? "+" : "";
}

// ── 1 · Saldo total ──────────────────────────────────────────────────────────

function SaldoTotal({ datos, variante, className }: WidgetProps) {
  const [abierto, setAbierto] = useState(false);
  const saldo = Number(datos.saldo_total);
  const puntos = datos.tendencia_saldo ?? [];

  // El cierre del mes pasado es el penúltimo punto de la tendencia: sale gratis
  const anterior = puntos.length >= 2 ? Number(puntos[puntos.length - 2].saldo) : null;
  const delta = anterior !== null ? saldo - anterior : null;
  const pct = anterior !== null ? variacion(saldo, anterior) : null;
  const cuentas = datos.saldos_por_cuenta;

  return (
    <BentoCard id="saldo-total" titulo="Saldo total" className={className}>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <p className="text-[2.25rem] font-bold leading-none tracking-tight tnum">{money(saldo)}</p>
        {pct !== null && (
          <Badge tono={delta! >= 0 ? "good" : "bad"}>
            {signo(pct)}
            {pct.toFixed(1)}%
          </Badge>
        )}
      </div>

      {delta !== null && (
        <p className="mt-1.5 text-sm text-ink-2">
          {money(Math.abs(delta))} {delta >= 0 ? "más" : "menos"} que al cierre del mes pasado
        </p>
      )}

      {/* En escritorio esta curva ya está, en grande, en su propio widget */}
      {variante === "compact" && puntos.length >= 2 && (
        <Suspense fallback={<div className="mt-4 h-14 animate-pulse rounded-lg bg-card-soft" />}>
          <MiniLinea puntos={puntos} />
        </Suspense>
      )}

      {cuentas.length > 0 && (
        <>
          <div className="my-4 border-t border-hairline" />
          {(abierto || cuentas.length <= 2) && (
            <ul className="space-y-3">
              {cuentas.map((c, i) => (
                <li key={c.cuenta_id} className="flex items-center gap-3 text-[15px]">
                  <span
                    aria-hidden
                    className="size-2 shrink-0 rounded-full"
                    style={{ background: colorSerie(i) }}
                  />
                  <span className="truncate text-ink-2">{c.nombre}</span>
                  <span className="ml-auto shrink-0 font-semibold tnum">
                    {money(Number(c.saldo))}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {cuentas.length > 2 && (
            <button
              onClick={() => setAbierto((v) => !v)}
              aria-expanded={abierto}
              className="mt-4 flex items-center gap-1 text-sm font-semibold text-accent"
            >
              {abierto ? "Ocultar desglose" : `Ver las ${cuentas.length} cuentas`}
              <ChevronDown size={16} className={cn("transition-transform", abierto && "rotate-180")} />
            </button>
          )}
        </>
      )}
    </BentoCard>
  );
}

// ── 2 y 3 · Ingresos y gastos ────────────────────────────────────────────────

function nombreMes(datos: DashboardResumen): string {
  const meses = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
  ];
  return meses[datos.periodo.mes - 1];
}

function Ingresos({ datos, className }: WidgetProps) {
  const total = Number(datos.ingresos_mes);
  const pct = variacion(total, datos.promedio_previos?.ingresos ?? 0);
  const ultimo = (datos.ultimos_movimientos ?? []).find((m) => m.tipo === "ingreso");

  return (
    <BentoCard id="ingresos" titulo={`Ingresos de ${nombreMes(datos)}`} className={className}>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <p className="text-[2.25rem] font-bold leading-none tracking-tight tnum">{money(total)}</p>
        {pct !== null && total > 0 && (
          <Badge tono={pct >= 0 ? "good" : "warn"}>
            {signo(pct)}
            {Math.round(pct)}% vs promedio
          </Badge>
        )}
      </div>

      {total > 0 ? (
        <Desglose
          partes={datos.ingresos_por_categoria ?? []}
          total={total}
          desplazar={6}
        />
      ) : (
        <p className="mt-4 text-sm text-ink-3">
          No registraste ingresos este mes.
          {ultimo && ` El último fue el ${fechaCorta(ultimo.fecha)}, por ${money(Number(ultimo.monto))}.`}
        </p>
      )}
    </BentoCard>
  );
}

function Gastos({ datos, className }: WidgetProps) {
  const total = Number(datos.gastos_mes);
  const ingresos = Number(datos.ingresos_mes);
  const pct = variacion(total, datos.promedio_previos?.gastos ?? 0);

  // Con ingresos del mes, la referencia útil es qué proporción se llevaron
  const ratio = ingresos > 0 ? Math.round((total / ingresos) * 100) : null;

  return (
    <BentoCard id="gastos" titulo={`Gastos de ${nombreMes(datos)}`} className={className}>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <p className="text-[2.25rem] font-bold leading-none tracking-tight tnum">{money(total)}</p>
        {ratio !== null ? (
          <Badge tono={ratio > 100 ? "bad" : ratio > 80 ? "warn" : "good"}>
            {ratio}% de tus ingresos
          </Badge>
        ) : (
          pct !== null &&
          total > 0 && (
            <Badge tono={pct > 25 ? "warn" : "neutro"}>
              {signo(pct)}
              {Math.round(pct)}% vs promedio
            </Badge>
          )
        )}
      </div>

      {total > 0 ? (
        <Desglose partes={datos.por_categoria ?? []} total={total} desplazar={1} />
      ) : (
        <p className="mt-4 text-sm text-ink-3">Todavía no registraste gastos este mes.</p>
      )}
    </BentoCard>
  );
}

// ── 4 · Tendencia (solo escritorio) ──────────────────────────────────────────

function Tendencia({ datos, className }: WidgetProps) {
  const puntos = datos.tendencia_saldo ?? [];

  return (
    <BentoCard
      id="tendencia-saldo"
      titulo="Tendencia de saldo"
      subtitulo={`Saldo al cierre de los últimos ${puntos.length || 6} meses`}
      className={className}
    >
      <div className="mt-3">
        <Suspense fallback={<div className="h-52 animate-pulse rounded-xl bg-card-soft" />}>
          <LineaSaldo puntos={puntos} />
        </Suspense>
      </div>
    </BentoCard>
  );
}

// ── 5 · Últimos registros ────────────────────────────────────────────────────

function UltimosRegistros({ datos, className }: WidgetProps) {
  const movs = datos.ultimos_movimientos ?? [];

  return (
    <BentoCard id="ultimos-registros" titulo="Últimos registros" className={className}>
      {movs.length === 0 ? (
        <p className="mt-4 text-sm text-ink-3">Todavía no registraste movimientos.</p>
      ) : (
        <>
          <ul className="mt-3 space-y-1">
            {movs.map((m) => (
              <Fila key={`${m.tipo}-${m.id}`} mov={m} />
            ))}
          </ul>
          <Link
            to="/movimientos"
            className="mt-4 flex items-center gap-1 text-sm font-semibold text-accent"
          >
            Ver todos los movimientos
            <ChevronRight size={16} />
          </Link>
        </>
      )}
    </BentoCard>
  );
}

function Fila({ mov }: { mov: MovimientoReciente }) {
  const entra = mov.tipo === "ingreso";
  return (
    <li className="flex items-center gap-3 py-1.5">
      <IconoTile categoria={mov.categoria} ingreso={entra} tamano="size-9" />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] font-semibold">
          {mov.descripcion?.trim() || mov.categoria || (entra ? "Ingreso" : "Gasto")}
        </span>
        <span className="block truncate text-xs text-ink-3">
          {fechaCorta(mov.fecha)}
          {mov.categoria && ` · ${mov.categoria}`}
        </span>
      </span>
      <span className={cn("shrink-0 font-semibold tnum", entra && "text-good-ink")}>
        {entra ? "+" : "−"}
        {money(Number(mov.monto))}
      </span>
    </li>
  );
}

/** 'Hoy' y 'Ayer' se leen más rápido que una fecha en una lista corta. */
function fechaCorta(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const dia = d.toLocaleDateString("sv-SE");
  const hoy = new Date().toLocaleDateString("sv-SE");
  const ayer = new Date(Date.now() - 86_400_000).toLocaleDateString("sv-SE");
  if (dia === hoy) return "Hoy";
  if (dia === ayer) return "Ayer";
  return d.toLocaleDateString("es-PE", { day: "numeric", month: "short" });
}

// ── 6 · Insights ─────────────────────────────────────────────────────────────

const TONO_INSIGHT: Record<SeveridadInsight, { raya: string; chip: string; icono: typeof Sparkles }> = {
  critico: { raya: "bg-bad-ink", chip: "bg-bad-soft text-bad-ink", icono: AlertTriangle },
  atencion: { raya: "bg-warn-ink", chip: "bg-warn-soft text-warn-ink", icono: TrendingUp },
  info: { raya: "bg-accent", chip: "bg-accent-soft text-accent-ink", icono: Sparkles },
};

function Insights({ variante, className }: WidgetProps) {
  const { data, isPending } = useInsights();
  const marcar = useMarcarInsight();
  const items = data?.items ?? [];

  return (
    <BentoCard
      id="insights"
      titulo="Insights"
      subtitulo={
        data?.generado_en
          ? `Generados el ${fechaCorta(data.generado_en).toLowerCase()}`
          : "Se generan solos cada lunes"
      }
      className={className}
    >
      {isPending ? (
        <div className="mt-4 space-y-2">
          {[0, 1].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-card-soft" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent-ink">
            <Sparkles size={20} />
          </span>
          <p className="min-w-0 flex-1 text-sm text-ink-2">
            Cada lunes se revisan tus últimos meses y aparece acá lo que valga la pena mirar.
            Hacen falta unos cuantos movimientos registrados.
          </p>
        </div>
      ) : (
        <ul
          className={cn(
            "mt-3 gap-2",
            // En escritorio la tarjeta ocupa el ancho completo: en columnas se lee mejor
            variante === "compact" ? "flex flex-col" : "grid sm:grid-cols-2 xl:grid-cols-4",
          )}
        >
          {items.map((i) => {
            const { raya } = TONO_INSIGHT[i.severidad];
            return (
              <li
                key={i.id}
                className={cn(
                  "flex gap-2.5 rounded-xl p-3",
                  i.leido ? "opacity-50" : "bg-card-soft",
                )}
              >
                <span aria-hidden className={cn("w-[3px] shrink-0 rounded-full", raya)} />
                <div className="min-w-0 flex-1">
                  <p className="text-[13.5px] font-semibold">{i.titulo}</p>
                  {i.detalle && <p className="mt-0.5 text-xs text-ink-2">{i.detalle}</p>}
                </div>
                {!i.leido && (
                  <button
                    onClick={() => marcar.mutate(i.id)}
                    aria-label={`Marcar como leído: ${i.titulo}`}
                    className="size-7 shrink-0 rounded-lg text-ink-3 transition-colors hover:bg-card hover:text-ink"
                  >
                    <Check size={15} className="mx-auto" />
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </BentoCard>
  );
}
