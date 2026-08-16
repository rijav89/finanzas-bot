import { lazy, Suspense } from "react";

import type { DashboardResumen } from "@/api/types";
import { BentoCard } from "@/components/bento/BentoCard";
import { Semaforo } from "@/components/ui/Semaforo";
import { money } from "@/lib/money";
import type { WidgetId } from "@/stores/bentoStore";

const SankeyFlujo = lazy(() =>
  import("@/components/charts/SankeyFlujo").then((m) => ({ default: m.SankeyFlujo })),
);

export interface WidgetProps {
  datos: DashboardResumen;
  variante: "compact" | "full";
  /** col-span de la celda: lo aplica el propio BentoCard, que es el nodo sortable. */
  className?: string;
}

/** Registro de widgets: prioridad ≤ 3 se muestra en móvil; el resto solo en desktop. */
export const REGISTRO: Record<
  WidgetId,
  { prioridad: number; span: string; Componente: (p: WidgetProps) => JSX.Element }
> = {
  "saldo-total": { prioridad: 1, span: "lg:col-span-3", Componente: SaldoTotal },
  "gasto-mes": { prioridad: 2, span: "lg:col-span-3", Componente: GastoMes },
  insights: { prioridad: 3, span: "lg:col-span-2", Componente: Insights },
  sankey: { prioridad: 4, span: "sm:col-span-2 lg:col-span-4", Componente: Sankey },
  categorias: { prioridad: 5, span: "lg:col-span-2", Componente: Categorias },
};

function SaldoTotal({ datos, className }: WidgetProps) {
  const saldo = Number(datos.saldo_total);
  return (
    <BentoCard
      id="saldo-total"
      titulo="Saldo total"
      className={className}
      desglose={
        <ul className="space-y-2">
          {datos.saldos_por_cuenta.map((c) => (
            <li key={c.cuenta_id} className="flex items-baseline justify-between gap-3 text-sm">
              <span className="text-ink-2">{c.nombre}</span>
              <span className="font-medium tabular-nums">{money(Number(c.saldo))}</span>
            </li>
          ))}
        </ul>
      }
    >
      <p className="text-[1.75rem] font-semibold leading-tight tracking-tight sm:text-3xl">{money(saldo)}</p>
      <div className="mt-2">
        {saldo < 0 ? (
          <Semaforo estado="critical" etiqueta="Saldo negativo" />
        ) : saldo < 100 ? (
          <Semaforo estado="warning" etiqueta="Saldo bajo" />
        ) : (
          <Semaforo
            estado="good"
            etiqueta={
              datos.saldos_por_cuenta.length === 1
                ? "1 cuenta"
                : `${datos.saldos_por_cuenta.length} cuentas`
            }
          />
        )}
      </div>
    </BentoCard>
  );
}

function GastoMes({ datos, className }: WidgetProps) {
  const gastos = Number(datos.gastos_mes);
  const ingresos = Number(datos.ingresos_mes);
  const ratio = ingresos > 0 ? gastos / ingresos : null;

  return (
    <BentoCard
      id="gasto-mes"
      titulo="Gastos del mes"
      className={className}
      desglose={
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-ink-2">Ingresos</dt>
            <dd className="font-medium tabular-nums">{money(ingresos)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-ink-2">Gastos</dt>
            <dd className="font-medium tabular-nums">{money(gastos)}</dd>
          </div>
          <div className="flex justify-between border-t border-hairline pt-2">
            <dt className="text-ink-2">Diferencia</dt>
            <dd className="font-medium tabular-nums">{money(ingresos - gastos)}</dd>
          </div>
        </dl>
      }
    >
      <p className="text-[1.75rem] font-semibold leading-tight tracking-tight sm:text-3xl">{money(gastos)}</p>
      <div className="mt-2">
        {ratio === null ? (
          <Semaforo estado="info" etiqueta="Sin ingresos este mes" />
        ) : ratio > 1 ? (
          <Semaforo estado="critical" etiqueta="Gastas más de lo que ingresas" />
        ) : ratio > 0.8 ? (
          <Semaforo estado="warning" etiqueta={`${Math.round(ratio * 100)}% de tus ingresos`} />
        ) : (
          <Semaforo estado="good" etiqueta={`${Math.round(ratio * 100)}% de tus ingresos`} />
        )}
      </div>
    </BentoCard>
  );
}

function Insights({ variante, className }: WidgetProps) {
  return (
    <BentoCard id="insights" titulo="Insights" className={className}>
      <p className="text-sm text-ink-3">
        Los análisis automáticos llegan en la próxima fase.
        {variante === "full" && " Se generan cada lunes de madrugada."}
      </p>
    </BentoCard>
  );
}

function Sankey({ datos, className }: WidgetProps) {
  return (
    <BentoCard id="sankey" titulo="Flujo del mes" className={className}>
      <Suspense fallback={<div className="h-64 animate-pulse rounded-xl bg-page sm:h-72" />}>
        <SankeyFlujo datos={datos} />
      </Suspense>
    </BentoCard>
  );
}

function Categorias({ datos, className }: WidgetProps) {
  const top = [...datos.por_categoria]
    .sort((a, b) => Number(b.total) - Number(a.total))
    .slice(0, 5);
  const max = Math.max(...top.map((c) => Number(c.total)), 1);

  return (
    <BentoCard id="categorias" titulo="Por categoría" className={className}>
      {top.length === 0 ? (
        <p className="text-sm text-ink-3">Sin gastos este mes.</p>
      ) : (
        <ul className="space-y-3">
          {top.map((c) => (
            <li key={c.categoria}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="truncate text-ink-2">{c.categoria}</span>
                <span className="shrink-0 font-medium tabular-nums">
                  {money(Number(c.total))}
                </span>
              </div>
              {/* Riel de fondo: la barra se lee como proporción, no como longitud suelta */}
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-page">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(Number(c.total) / max) * 100}%`,
                    background: "var(--series-1)",
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </BentoCard>
  );
}
