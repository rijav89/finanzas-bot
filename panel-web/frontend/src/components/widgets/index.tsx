import { Bell, ChevronDown, ChevronRight, Sparkles } from "lucide-react";
import { lazy, Suspense, useState } from "react";
import { Link } from "react-router-dom";

import type { DashboardResumen } from "@/api/types";
import { BentoCard } from "@/components/bento/BentoCard";
import { Badge } from "@/components/ui/Badge";
import { BarraProgreso } from "@/components/ui/BarraProgreso";
import { cn } from "@/lib/cn";
import { money } from "@/lib/money";
import type { WidgetId } from "@/stores/bentoStore";

const SankeyFlujo = lazy(() =>
  import("@/components/charts/SankeyFlujo").then((m) => ({ default: m.SankeyFlujo })),
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

function Insights({ className }: WidgetProps) {
  return (
    <BentoCard id="insights" titulo="Insights · próximamente" className={className}>
      <div className="mt-4 flex flex-wrap items-center gap-4">
        <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent-ink">
          <Sparkles size={22} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold">Análisis automáticos de tus hábitos</p>
          <p className="mt-0.5 text-sm text-ink-2">
            Detección de gastos inusuales, proyección de fin de mes y sugerencias de tope.
          </p>
        </div>
        <button className="flex h-10 shrink-0 items-center gap-2 rounded-xl bg-card px-4 text-sm font-semibold text-ink-2 shadow-sm ring-1 ring-[var(--ring)]">
          <Bell size={16} />
          Avisame
        </button>
      </div>
    </BentoCard>
  );
}
