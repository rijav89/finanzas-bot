import type { CategoriaResumen } from "@/api/types";
import { colorSerie } from "@/lib/series";
import { money } from "@/lib/money";

/** Barra apilada + leyenda: en qué se reparte un total.
 *
 *  La usan los widgets de ingresos y de gastos con el mismo formato, para que
 *  comparar los dos lados del mes sea leer la misma figura dos veces.
 */
export function Desglose({
  partes,
  total,
  maximo = 6,
  desplazar = 0,
}: {
  partes: CategoriaResumen[];
  total: number;
  /** Más allá de esto las franjas son hilos: el resto se agrupa. */
  maximo?: number;
  /** Corre la paleta para que ingresos y gastos no usen los mismos colores. */
  desplazar?: number;
}) {
  const orden = [...partes].sort((a, b) => Number(b.total) - Number(a.total));
  const visibles = orden.slice(0, maximo).map((c) => ({
    id: c.categoria,
    valor: Number(c.total),
  }));
  const resto = total - visibles.reduce((s, p) => s + p.valor, 0);
  if (resto > 0.005) visibles.push({ id: "Otras", valor: resto });

  if (total <= 0 || visibles.length === 0) return null;

  const pct = (v: number) => (v / total) * 100;

  return (
    <>
      <div
        className="mt-3 flex h-3 gap-0.5"
        role="img"
        aria-label={visibles.map((p) => `${p.id}: ${money(p.valor)}`).join(", ")}
      >
        {visibles.map((p, i) => (
          <span
            key={p.id}
            className="block first:rounded-l-full last:rounded-r-full"
            style={{ width: `${pct(p.valor)}%`, background: colorSerie(i, desplazar) }}
          />
        ))}
      </div>

      <ul className="mt-3 space-y-2">
        {visibles.map((p, i) => (
          <li key={p.id} className="flex items-center gap-2.5 text-sm">
            <span
              aria-hidden
              className="size-2 shrink-0 rounded-full"
              style={{ background: colorSerie(i, desplazar) }}
            />
            <span className="min-w-0 flex-1 truncate text-ink-2">{p.id}</span>
            <span className="shrink-0 text-xs text-ink-3 tnum">{Math.round(pct(p.valor))}%</span>
            <span className="shrink-0 font-semibold tnum">{money(p.valor)}</span>
          </li>
        ))}
      </ul>
    </>
  );
}
