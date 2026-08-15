import { ResponsiveSankey } from "@nivo/sankey";

import type { DashboardResumen } from "@/api/types";
import { money } from "@/lib/money";

/** Río de dinero: Ingresos → Gastos por categoría / Sin asignar.
 *  Colores por rol (tokens del sistema), texto siempre en tinta, nunca en color de serie. */
export function SankeyFlujo({ datos }: { datos: DashboardResumen }) {
  const ingresos = Number(datos.ingresos_mes) || 0;
  const gastos = Number(datos.gastos_mes) || 0;
  const restante = Math.max(ingresos - gastos, 0);

  // Máximo 4 categorías + "Otras": más nodos hacen ilegible el diagrama
  const top = [...datos.por_categoria]
    .sort((a, b) => Number(b.total) - Number(a.total))
    .slice(0, 4);
  const resto = gastos - top.reduce((s, c) => s + Number(c.total), 0);

  const nodes = [
    { id: "Ingresos" },
    ...top.map((c) => ({ id: c.categoria })),
    ...(resto > 0.005 ? [{ id: "Otras" }] : []),
    ...(restante > 0.005 ? [{ id: "Disponible" }] : []),
  ];

  const links = [
    ...top.map((c) => ({ source: "Ingresos", target: c.categoria, value: Number(c.total) })),
    ...(resto > 0.005 ? [{ source: "Ingresos", target: "Otras", value: resto }] : []),
    ...(restante > 0.005
      ? [{ source: "Ingresos", target: "Disponible", value: restante }]
      : []),
  ];

  if (links.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-ink-3">
        Aún no hay ingresos ni gastos este mes.
      </p>
    );
  }

  return (
    <div className="h-64 sm:h-72">
      <ResponsiveSankey
        data={{ nodes, links }}
        margin={{ top: 8, right: 96, bottom: 8, left: 76 }}
        align="justify"
        colors={[
          "var(--series-1)",
          "var(--series-2)",
          "var(--series-3)",
          "var(--seq-300)",
          "var(--seq-600)",
          "var(--status-good)",
        ]}
        nodeOpacity={1}
        nodeThickness={14}
        nodeBorderWidth={0}
        nodeSpacing={16}
        linkOpacity={0.35}
        linkHoverOpacity={0.6}
        enableLinkGradient
        labelPosition="outside"
        labelPadding={10}
        labelTextColor="var(--ink-secondary)"
        animate={false}
        nodeTooltip={({ node }) => (
          <Tooltip titulo={node.id as string} valor={node.value as number} />
        )}
        linkTooltip={({ link }) => (
          <Tooltip
            titulo={`${link.source.id} → ${link.target.id}`}
            valor={link.value as number}
          />
        )}
      />
    </div>
  );
}

function Tooltip({ titulo, valor }: { titulo: string; valor: number }) {
  return (
    <div className="rounded-lg bg-card px-2.5 py-1.5 text-xs shadow-lg ring-1 ring-[var(--border-ring)]">
      <div className="text-ink-2">{titulo}</div>
      <div className="font-medium text-ink">{money(valor)}</div>
    </div>
  );
}
