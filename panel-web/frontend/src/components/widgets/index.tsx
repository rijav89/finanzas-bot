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
}

/** Registro de widgets: prioridad ≤ 3 se muestra en móvil; el resto solo en desktop. */
export const REGISTRO: Record<
  WidgetId,
  { prioridad: number; span: string; Componente: (p: WidgetProps) => JSX.Element }
> = {
  "saldo-total": { prioridad: 1, span: "lg:col-span-2", Componente: SaldoTotal },
  "gasto-mes": { prioridad: 2, span: "lg:col-span-2", Componente: GastoMes },
  insights: { prioridad: 3, span: "lg:col-span-2", Componente: Insights },
  sankey: { prioridad: 4, span: "sm:col-span-2 lg:col-span-4", Componente: Sankey },
  categorias: { prioridad: 5, span: "lg:col-span-2", Componente: Categorias },
};

function SaldoTotal({ datos }: WidgetProps) {
  const saldo = Number(datos.saldo_total);
  return (
    <BentoCard
      id="saldo-total"
      titulo="Saldo total"
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
      <p className="text-3xl font-semibold tracking-tight">{money(saldo)}</p>
      <div className="mt-2">
        {saldo < 0 ? (
          <Semaforo estado="critical" etiqueta="Saldo negativo" />
        ) : saldo < 100 ? (
          <Semaforo estado="warning" etiqueta="Saldo bajo" />
        ) : (
          <Semaforo estado="good" etiqueta={`${datos.saldos_por_cuenta.length} cuentas`} />
        )}
      </div>
    </BentoCard>
  );
}

function GastoMes({ datos }: WidgetProps) {
  const gastos = Number(datos.gastos_mes);
  const ingresos = Number(datos.ingresos_mes);
  const ratio = ingresos > 0 ? gastos / ingresos : null;

  return (
    <BentoCard
      id="gasto-mes"
      titulo="Gastos del mes"
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
      <p className="text-3xl font-semibold tracking-tight">{money(gastos)}</p>
      <div className="mt-2">
        {ratio === null ? (
          <Semaforo estado="info" etiqueta="Sin ingresos registrados" />
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

function Insights({ variante }: WidgetProps) {
  return (
    <BentoCard id="insights" titulo="Insights">
      <p className="text-sm text-ink-3">
        Los análisis automáticos llegan en la próxima fase.
        {variante === "full" && " Se generan cada lunes de madrugada."}
      </p>
    </BentoCard>
  );
}

function Sankey({ datos }: WidgetProps) {
  return (
    <BentoCard id="sankey" titulo="Flujo del mes">
      <Suspense
        fallback={<div className="h-64 animate-pulse rounded-xl bg-page sm:h-72" />}
      >
        <SankeyFlujo datos={datos} />
      </Suspense>
    </BentoCard>
  );
}

function Categorias({ datos }: WidgetProps) {
  const top = [...datos.por_categoria]
    .sort((a, b) => Number(b.total) - Number(a.total))
    .slice(0, 5);
  const max = Math.max(...top.map((c) => Number(c.total)), 1);

  return (
    <BentoCard id="categorias" titulo="Por categoría">
      {top.length === 0 ? (
        <p className="text-sm text-ink-3">Sin gastos este mes.</p>
      ) : (
        <ul className="space-y-2.5">
          {top.map((c) => (
            <li key={c.categoria}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="text-ink-2">{c.categoria}</span>
                <span className="font-medium tabular-nums">{money(Number(c.total))}</span>
              </div>
              <div
                className="mt-1 h-1.5 rounded-full"
                style={{
                  width: `${(Number(c.total) / max) * 100}%`,
                  background: "var(--series-1)",
                }}
              />
            </li>
          ))}
        </ul>
      )}
    </BentoCard>
  );
}
