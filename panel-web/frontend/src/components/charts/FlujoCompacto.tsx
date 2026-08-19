import type { DashboardResumen } from "@/api/types";
import { calcularFlujo, SERIES, type Parte } from "@/components/charts/flujo";
import { money } from "@/lib/money";

/** El flujo del mes para pantallas angostas.
 *
 *  Dice lo mismo que el Sankey —de dónde vino la plata y en qué se fue— pero apilado
 *  en vertical, que es como se lee un celular. No importa nada de Nivo: en una
 *  tarjeta de 330 px las bandas cruzadas quedan ilegibles y no justifican 74 KB.
 */
export function FlujoCompacto({ datos }: { datos: DashboardResumen }) {
  const { origenes, destinos, total } = calcularFlujo(datos);

  if (total <= 0) {
    return (
      <p className="py-8 text-center text-sm text-ink-3">
        Cuando registres movimientos verás acá cómo se reparte tu plata.
      </p>
    );
  }

  return (
    <div className="mt-4 space-y-5">
      <Tramo titulo="De dónde vino" partes={origenes} total={total} desplazar={0} />
      <Tramo titulo="En qué se fue" partes={destinos} total={total} desplazar={origenes.length} />
    </div>
  );
}

function Tramo({
  titulo,
  partes,
  total,
  desplazar,
}: {
  titulo: string;
  partes: Parte[];
  total: number;
  /** Corre la paleta para que un origen y un destino no compartan color. */
  desplazar: number;
}) {
  const color = (i: number) => SERIES[(i + desplazar) % SERIES.length];

  return (
    <section>
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold text-ink-2">{titulo}</h3>
        <span className="text-sm font-bold tnum">{money(total)}</span>
      </div>

      <div
        className="mt-2 flex h-3 gap-0.5 overflow-hidden rounded-full"
        role="img"
        aria-label={partes.map((p) => `${p.id}: ${money(p.valor)}`).join(", ")}
      >
        {partes.map((p, i) => (
          <span
            key={p.id}
            style={{ width: `${(p.valor / total) * 100}%`, background: color(i) }}
            className="first:rounded-l-full last:rounded-r-full"
          />
        ))}
      </div>

      <ul className="mt-3 space-y-2">
        {partes.map((p, i) => (
          <li key={p.id} className="flex items-center gap-2.5 text-sm">
            <span
              aria-hidden
              className="size-2 shrink-0 rounded-full"
              style={{ background: color(i) }}
            />
            <span className="min-w-0 flex-1 truncate text-ink-2">{p.id}</span>
            <span className="shrink-0 text-xs text-ink-3 tnum">
              {Math.round((p.valor / total) * 100)}%
            </span>
            <span className="shrink-0 font-semibold tnum">{money(p.valor)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
