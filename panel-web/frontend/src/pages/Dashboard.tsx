import { useDashboard } from "@/api/queries";
import { BentoGrid } from "@/components/bento/BentoGrid";
import { REGISTRO } from "@/components/widgets";
import { useVariant } from "@/hooks/useVariant";
import { useBentoStore } from "@/stores/bentoStore";

export default function Dashboard() {
  const { data, isPending, isError } = useDashboard();
  const orden = useBentoStore((s) => s.orden);
  const variante = useVariant();

  if (isPending) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-6">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-2xl bg-card lg:col-span-2" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return <p className="text-sm text-critical">No se pudo cargar el panel.</p>;
  }

  // Móvil: solo lo crítico y accionable (prioridad ≤ 3). Desktop: panorámica completa.
  // Es jerarquía de contenido deliberada, no una versión "reducida".
  const visibles = orden.filter((id) =>
    variante === "compact" ? REGISTRO[id].prioridad <= 3 : true,
  );

  return (
    <>
      <h1 className="mb-4 hidden text-2xl font-semibold lg:block">Panel</h1>
      <BentoGrid ids={visibles}>
        {visibles.map((id) => {
          const { Componente, span } = REGISTRO[id];
          return (
            <div key={id} className={span}>
              <Componente datos={data} variante={variante} />
            </div>
          );
        })}
      </BentoGrid>
      {variante === "compact" && (
        <p className="mt-4 text-center text-xs text-ink-3">
          El análisis detallado vive en Movimientos y Reportes.
        </p>
      )}
    </>
  );
}
