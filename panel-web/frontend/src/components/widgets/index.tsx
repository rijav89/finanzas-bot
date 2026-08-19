import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { lazy, Suspense, useState } from "react";
import { Link } from "react-router-dom";

import { useInsights, useMarcarInsight } from "@/api/queries";
import type { DashboardResumen, SeveridadInsight } from "@/api/types";
import { BentoCard } from "@/components/bento/BentoCard";
import { Badge } from "@/components/ui/Badge";
import { BarraProgreso } from "@/components/ui/BarraProgreso";
import { cn } from "@/lib/cn";
import { IconoTile } from "@/lib/iconos";
import { money } from "@/lib/money";
import type { WidgetId } from "@/stores/bentoStore";

const SankeyFlujo = lazy(() =>
  import("@/components/charts/SankeyFlujo").then((m) => ({ default: m.SankeyFlujo })),
);
const LineaSaldo = lazy(() =>
  import("@/components/charts/LineaSaldo").then((m) => ({ default: m.LineaSaldo })),
);

/** Colores de serie para cuentas y categorías, en el orden del mockup. */
export const SERIES = [
  "var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)",
  "var(--s5)", "var(--s6)", "var(--s7)",
];

export interface WidgetProps {
  datos: DashboardResumen;
  variante: "compact" | "full";
  className?: string;
}

/** prioridad ≤ 2 se muestra en móvil; el resto vive en escritorio. */
export const REGISTRO: Record<
  WidgetId,
  { prioridad: number; span: string; Componente: (p: WidgetProps) => JSX.Element }
> = {
  "saldo-total": { prioridad: 1, span: "lg:col-span-3", Componente: SaldoTotal },
  "gasto-mes": { prioridad: 2, span: "lg:col-span-3", Componente: GastoMes },
  "tendencia-saldo": { prioridad: 3, span: "lg:col-span-4", Componente: Tendencia },
  "ultimos-ingresos": { prioridad: 3, span: "lg:col-span-2", Componente: UltimosIngresos },
  sankey: { prioridad: 4, span: "lg:col-span-4", Componente: Flujo },
  categorias: { prioridad: 5, span: "lg:col-span-2", Componente: Categorias },
  insights: { prioridad: 6, span: "lg:col-span-6", Componente: Insights },
};

function SaldoTotal({ datos, className }: WidgetProps) {
  const [abierto, setAbierto] = useState(true);
  const saldo = Number(datos.saldo_total);

  return (
    <BentoCard id="saldo-total" titulo="Saldo total" className={className}>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <p className="text-[2.5rem] font-bold leading-none tracking-tight tnum">
          {money(saldo)}
        </p>
        {saldo >= 0 ? (
          <Badge tono="good">Al día</Badge>
        ) : (
          <Badge tono="bad">En negativo</Badge>
        )}
      </div>

      {datos.saldos_por_cuenta.length > 0 && (
        <>
          <div className="my-4 border-t border-hairline" />
          {abierto && (
            <ul className="space-y-3">
              {datos.saldos_por_cuenta.map((c, i) => (
                <li key={c.cuenta_id} className="flex items-center gap-3 text-[15px]">
                  <span
                    aria-hidden
                    className="size-2 shrink-0 rounded-full"
                    style={{ background: SERIES[i % SERIES.length] }}
                  />
                  <span className="truncate text-ink-2">{c.nombre}</span>
                  <span className="ml-auto shrink-0 font-semibold tnum">
                    {money(Number(c.saldo))}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <button
            onClick={() => setAbierto((v) => !v)}
            aria-expanded={abierto}
            className="mt-4 flex items-center gap-1 text-sm font-semibold text-accent"
          >
            {abierto ? "Ocultar desglose" : "Ver desglose"}
            <ChevronDown size={16} className={cn("transition-transform", abierto && "rotate-180")} />
          </button>
        </>
      )}
    </BentoCard>
  );
}

function GastoMes({ datos, className }: WidgetProps) {
  const gastos = Number(datos.gastos_mes);
  const ingresos = Number(datos.ingresos_mes);
  const ratio = ingresos > 0 ? gastos / ingresos : null;
  const pct = ratio !== null ? Math.round(ratio * 100) : 0;

  const tono = ratio === null ? "neutro" : ratio > 0.8 ? "bad" : ratio > 0.5 ? "warn" : "good";

  return (
    <BentoCard id="gasto-mes" titulo="Gastos del mes" className={className}>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <p className="text-[2.5rem] font-bold leading-none tracking-tight tnum">{money(gastos)}</p>
        {ratio !== null ? (
          <Badge tono={tono}>{pct}% de tus ingresos</Badge>
        ) : (
          <Badge tono="neutro">Sin ingresos este mes</Badge>
        )}
      </div>

      <BarraProgreso
        className="mt-5"
        porcentaje={pct}
        tono={tono === "neutro" ? "accent" : tono}
      />
      <div className="mt-2 flex justify-between text-xs text-ink-3">
        <span>Zona segura hasta 50%</span>
        <span>Límite 80%</span>
      </div>

      <div className="my-4 border-t border-hairline" />

      <dl className="grid grid-cols-3 gap-3">
        <div>
          <dt className="text-xs text-ink-2">Ingresos</dt>
          <dd className="mt-1 text-xl font-bold text-good-ink tnum">{money(ingresos)}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-2">Gastos</dt>
          <dd className="mt-1 text-xl font-bold text-bad-ink tnum">{money(gastos)}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-2">Diferencia</dt>
          <dd className="mt-1 text-xl font-bold tnum">
            {ingresos - gastos >= 0 ? "+" : ""}
            {money(ingresos - gastos)}
          </dd>
        </div>
      </dl>
    </BentoCard>
  );
}

function Flujo({ datos, className }: WidgetProps) {
  const ingresos = Number(datos.ingresos_mes);
  const gastos = Number(datos.gastos_mes);

  // El subtítulo debe describir lo que el diagrama realmente muestra
  const subtitulo =
    ingresos === 0 && gastos > 0
      ? `Sin ingresos este mes: los ${money(gastos)} salieron de tu saldo`
      : ingresos > gastos
        ? `De tus ${money(ingresos)} de ingresos, ahorraste ${money(ingresos - gastos)}`
        : ingresos > 0
          ? `Gastaste ${money(gastos - ingresos)} más de lo que ingresó este mes`
          : "Cuando registres movimientos verás cómo se reparte tu plata";

  return (
    <BentoCard id="sankey" titulo="Flujo del mes" subtitulo={subtitulo} className={className}>
      <div className="mt-4">
        <Suspense fallback={<div className="h-72 animate-pulse rounded-xl bg-card-soft" />}>
          <SankeyFlujo datos={datos} />
        </Suspense>
      </div>
    </BentoCard>
  );
}

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

function UltimosIngresos({ datos, className }: WidgetProps) {
  const ingresos = datos.ultimos_ingresos ?? [];

  return (
    <BentoCard id="ultimos-ingresos" titulo="Últimos ingresos" className={className}>
      {ingresos.length === 0 ? (
        <p className="mt-4 text-sm text-ink-3">Todavía no registraste ingresos.</p>
      ) : (
        <>
          <ul className="mt-3 space-y-1">
            {ingresos.map((i) => (
              <li key={i.id} className="flex items-center gap-3 py-1.5">
                <IconoTile categoria={i.categoria} ingreso tamano="size-9" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[15px] font-semibold">
                    {i.descripcion?.trim() || i.categoria || "Ingreso"}
                  </span>
                  <span className="block truncate text-xs text-ink-3">
                    {fechaCorta(i.fecha)}
                    {i.cuenta && ` · ${i.cuenta}`}
                  </span>
                </span>
                <span className="shrink-0 font-semibold text-good-ink tnum">
                  +{money(Number(i.monto))}
                </span>
              </li>
            ))}
          </ul>
          <Link
            to="/movimientos?tipo=ingreso"
            className="mt-4 flex items-center gap-1 text-sm font-semibold text-accent"
          >
            Ver todos los ingresos
            <ChevronRight size={16} />
          </Link>
        </>
      )}
    </BentoCard>
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

function Categorias({ datos, className }: WidgetProps) {
  const orden = [...datos.por_categoria].sort((a, b) => Number(b.total) - Number(a.total));
  const top = orden.slice(0, 5);
  const max = Math.max(...top.map((c) => Number(c.total)), 1);

  return (
    <BentoCard id="categorias" titulo="Por categoría" className={className}>
      {top.length === 0 ? (
        <p className="mt-4 text-sm text-ink-3">Sin gastos este mes.</p>
      ) : (
        <>
          <ul className="mt-4 space-y-4">
            {top.map((c, i) => (
              <li key={c.categoria}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="truncate font-semibold">{c.categoria}</span>
                  <span className="shrink-0 font-semibold tnum">{money(Number(c.total))}</span>
                </div>
                <BarraProgreso
                  className="mt-2"
                  altura="h-1.5"
                  porcentaje={(Number(c.total) / max) * 100}
                  color={SERIES[i % SERIES.length]}
                />
              </li>
            ))}
          </ul>
          {orden.length > 5 && (
            <Link
              to="/movimientos"
              className="mt-5 flex items-center gap-1 text-sm font-semibold text-accent"
            >
              Ver las {orden.length} categorías
              <ChevronRight size={16} />
            </Link>
          )}
        </>
      )}
    </BentoCard>
  );
}

const TONO_INSIGHT: Record<SeveridadInsight, { chip: string; icono: typeof Sparkles }> = {
  critico: { chip: "bg-bad-soft text-bad-ink", icono: AlertTriangle },
  atencion: { chip: "bg-warn-soft text-warn-ink", icono: TrendingUp },
  info: { chip: "bg-accent-soft text-accent-ink", icono: Sparkles },
};

function Insights({ className }: WidgetProps) {
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
            <div key={i} className="h-16 animate-pulse rounded-xl bg-card-soft" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent-ink">
            <Sparkles size={22} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-semibold">Todavía no hay análisis</p>
            <p className="mt-0.5 text-sm text-ink-2">
              Cada lunes se revisan tus últimos meses y aparecen acá los patrones que
              valga la pena mirar. Hacen falta unos cuantos movimientos registrados.
            </p>
          </div>
        </div>
      ) : (
        <ul className="mt-4 space-y-2">
          {items.map((i) => {
            const { chip, icono: Icono } = TONO_INSIGHT[i.severidad];
            return (
              <li
                key={i.id}
                className={cn(
                  "flex gap-3 rounded-xl p-3 transition-opacity",
                  i.leido ? "opacity-55" : "bg-card-soft",
                )}
              >
                <span
                  aria-hidden
                  className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg", chip)}
                >
                  <Icono size={17} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-baseline gap-x-2 font-semibold">
                    {i.titulo}
                    {i.metrica && (
                      <span className="text-sm font-bold text-ink-2 tnum">{i.metrica}</span>
                    )}
                  </p>
                  {i.detalle && <p className="mt-0.5 text-sm text-ink-2">{i.detalle}</p>}
                </div>
                {!i.leido && (
                  <button
                    onClick={() => marcar.mutate(i.id)}
                    aria-label={`Marcar como leído: ${i.titulo}`}
                    className="size-8 shrink-0 rounded-lg text-ink-3 transition-colors hover:bg-card hover:text-ink"
                  >
                    <Check size={16} className="mx-auto" />
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
