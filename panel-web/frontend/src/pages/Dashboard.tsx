import { Monitor } from "lucide-react";

import { useDashboard } from "@/api/queries";
import { BentoGrid } from "@/components/bento/BentoGrid";
import { AccionesHeader } from "@/components/layout/AccionesHeader";
import { HeaderMovil } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/ui/Card";
import { REGISTRO } from "@/components/widgets";
import { useVariant } from "@/hooks/useVariant";
import { money } from "@/lib/money";
import { useBentoStore } from "@/stores/bentoStore";

const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

export default function Dashboard() {
  const { data, isPending, isError } = useDashboard();
  const orden = useBentoStore((s) => s.orden);
  const variante = useVariant();

  if (isPending) {
    return (
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-6">
        {[0, 1].map((i) => (
          <div key={i} className="h-52 animate-pulse rounded-2xl bg-card lg:col-span-3" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return <p className="text-sm text-bad-ink">No se pudo cargar el panel.</p>;
  }

  const periodo = `${MESES[data.periodo.mes - 1]} ${data.periodo.anio}`;

  // Móvil: solo lo crítico (prioridad ≤ 2). Desktop: panorámica completa.
  // Es jerarquía de contenido deliberada, no una versión "reducida".
  const visibles = orden.filter((id) =>
    variante === "compact" ? REGISTRO[id].prioridad <= 2 : true,
  );

  return (
    <>
      <HeaderMovil
        titulo="Panel"
        subtitulo={`${MESES[data.periodo.mes - 1][0].toUpperCase()}${MESES[
          data.periodo.mes - 1
        ].slice(1)} ${data.periodo.anio} · ${money(Number(data.saldo_total))}`}
      />
      <div className="hidden lg:block">
        <PageHeader
          titulo="Panel"
          subtitulo={`Tu resumen de ${periodo}`}
          acciones={<AccionesHeader />}
        />
      </div>

      <BentoGrid ids={visibles}>
        {visibles.map((id) => {
          const { Componente, span } = REGISTRO[id];
          return <Componente key={id} datos={data} variante={variante} className={span} />;
        })}
      </BentoGrid>

      {variante === "compact" && (
        <div className="mt-4 flex items-center gap-3 rounded-2xl bg-card-soft p-4">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-card text-ink-3">
            <Monitor size={19} />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold">Tendencia de saldo</p>
            <p className="text-sm text-ink-3">
              La curva de 6 meses en grande se ve en escritorio
            </p>
          </div>
        </div>
      )}
    </>
  );
}
