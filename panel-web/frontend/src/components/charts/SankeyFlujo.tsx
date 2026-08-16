import { ResponsiveSankey } from "@nivo/sankey";

import type { DashboardResumen } from "@/api/types";
import { money } from "@/lib/money";

/** Río de dinero: Ingresos → Ahorro/categorías. Colores por rol (tokens del sistema);
 *  el texto va siempre en tinta, nunca en color de serie. */
export function SankeyFlujo({ datos }: { datos: DashboardResumen }) {
  const ingresos = Number(datos.ingresos_mes) || 0;
  const gastos = Number(datos.gastos_mes) || 0;
  const restante = Math.max(ingresos - gastos, 0);

  // Máximo 5 categorías + "Otros": más nodos hacen ilegible el diagrama
  const top = [...datos.por_categoria]
    .sort((a, b) => Number(b.total) - Number(a.total))
    .slice(0, 5);
  const resto = gastos - top.reduce((s, c) => s + Number(c.total), 0);

  const nodes = [
    { id: "Ingresos" },
    ...(restante > 0.005 ? [{ id: "Ahorro" }] : []),
    ...top.map((c) => ({ id: c.categoria })),
    ...(resto > 0.005 ? [{ id: "Otros" }] : []),
  ];

  const links = [
    ...(restante > 0.005
      ? [{ source: "Ingresos", target: "Ahorro", value: restante }]
      : []),
    ...top.map((c) => ({ source: "Ingresos", target: c.categoria, value: Number(c.total) })),
    ...(resto > 0.005 ? [{ source: "Ingresos", target: "Otros", value: resto }] : []),
  ];

  if (links.length === 0) {
    return (
      <p className="py-16 text-center text-sm text-ink-3">
        Aún no hay ingresos ni gastos este mes.
      </p>
    );
  }

  return (
    <div className="h-72 sm:h-80">
      <ResponsiveSankey
        data={{ nodes, links }}
        margin={{ top: 8, right: 110, bottom: 8, left: 84 }}
        align="justify"
        colors={[
          "var(--s1)", "var(--s7)", "var(--s2)", "var(--s3)",
          "var(--s4)", "var(--s5)", "var(--s6)",
        ]}
        nodeOpacity={1}
        nodeThickness={12}
        nodeBorderWidth={0}
        nodeBorderRadius={3}
        nodeSpacing={18}
        linkOpacity={0.32}
        linkHoverOpacity={0.55}
        enableLinkGradient
        labelPosition="outside"
        labelPadding={12}
        labelTextColor="var(--ink)"
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
    <div className="rounded-lg bg-card px-2.5 py-1.5 text-xs shadow-lg ring-1 ring-[var(--ring)]">
      <div className="text-ink-2">{titulo}</div>
      <div className="font-semibold text-ink tnum">{money(valor)}</div>
    </div>
  );
}
