import { useState } from "react";

import { useMovimientos } from "@/api/queries";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { money } from "@/lib/money";

const FILTROS = [
  { valor: "", etiqueta: "Todos" },
  { valor: "gasto", etiqueta: "Gastos" },
  { valor: "ingreso", etiqueta: "Ingresos" },
] as const;

export default function Movimientos() {
  const [tipo, setTipo] = useState("");
  const [q, setQ] = useState("");
  const { data, isPending } = useMovimientos({ tipo: tipo || undefined, q: q || undefined });

  return (
    <>
      <h1 className="mb-4 text-xl font-semibold lg:text-2xl">Movimientos</h1>

      <div className="mb-4 flex flex-wrap gap-2">
        {FILTROS.map((f) => (
          <button
            key={f.valor}
            onClick={() => setTipo(f.valor)}
            className={cn(
              "touch-44 rounded-xl px-4 text-sm ring-1 ring-[var(--border-ring)]",
              tipo === f.valor ? "bg-accent text-white" : "bg-card text-ink-2",
            )}
          >
            {f.etiqueta}
          </button>
        ))}
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar…"
          className="min-w-40 flex-1 touch-44 rounded-xl bg-card px-3 text-sm text-ink ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
        />
      </div>

      {isPending ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-2xl bg-card" />
          ))}
        </div>
      ) : !data?.items.length ? (
        <Card>
          <p className="text-sm text-ink-3">Sin movimientos que coincidan.</p>
        </Card>
      ) : (
        <ul className="space-y-2">
          {data.items.map((m) => (
            <li key={`${m.tipo}-${m.id}`}>
              <Card className="flex items-center gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {m.descripcion || m.categoria || "(sin descripción)"}
                  </p>
                  <p className="text-xs text-ink-3">
                    {m.categoria}
                    {m.fecha && ` · ${new Date(m.fecha).toLocaleDateString("es-PE")}`}
                  </p>
                </div>
                <span
                  className={cn(
                    "ml-auto shrink-0 font-medium tabular-nums",
                    m.tipo === "ingreso" ? "text-good-text" : "text-ink",
                  )}
                >
                  {m.tipo === "ingreso" ? "+" : "−"}
                  {money(Number(m.monto))}
                </span>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
