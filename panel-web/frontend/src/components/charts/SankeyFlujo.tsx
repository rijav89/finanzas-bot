import { ResponsiveSankey } from "@nivo/sankey";

import type { DashboardResumen } from "@/api/types";
import { calcularFlujo } from "@/components/charts/flujo";
import { money } from "@/lib/money";

/** Río de dinero del mes, para pantallas anchas.
 *
 *  Izquierda: de dónde salió la plata — tus fuentes de ingreso reales (Sueldo,
 *  Freelance…) y, si gastaste más de lo que entró, el "Saldo anterior" que cubre
 *  la diferencia. Derecha: en qué se fue, más "Ahorro" si sobró.
 *
 *  Importante: Nivo calcula el valor de cada nodo sumando sus enlaces, así que
 *  los nodos de origen deben sumar exactamente lo mismo que los de destino; si
 *  no, una etiqueta termina mostrando un número que no le corresponde. De eso se
 *  encarga `calcularFlujo`, compartido con la vista compacta de móvil.
 */
export function SankeyFlujo({ datos }: { datos: DashboardResumen }) {
  const { origenes, destinos, total: totalOrigen } = calcularFlujo(datos);

  if (origenes.length === 0 || destinos.length === 0) {
    return (
      <p className="py-20 text-center text-sm text-ink-3">
        Cuando registres movimientos verás acá cómo se reparte tu plata.
      </p>
    );
  }

  // Reparte cada origen entre los destinos en proporción, para que el total cuadre
  const links = origenes.flatMap((o) =>
    destinos
      .map((d) => ({
        source: o.id,
        target: d.id,
        value: (d.valor * o.valor) / totalOrigen,
      }))
      .filter((l) => l.value > 0.005),
  );

  const nodes = [...origenes.map((o) => ({ id: o.id })), ...destinos.map((d) => ({ id: d.id }))];

  return (
    <div className="h-72 sm:h-80">
      <ResponsiveSankey
        data={{ nodes, links }}
        margin={{ top: 8, right: 116, bottom: 8, left: 106 }}
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
