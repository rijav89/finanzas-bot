import { useEffect, useState } from "react";

import { useCrearGasto, useCuentas } from "@/api/queries";
import { CATEGORIAS } from "@/api/types";
import { Boton } from "@/components/ui/Boton";
import { useUiStore } from "@/stores/uiStore";

/** Formulario conversacional "Mad Libs":
 *  Hoy gasté [S/ __] en [Categoría ▾] pagando con [Cuenta ▾].
 *  Los selectores inline cumplen área táctil de 44px. */
export function GastoRapido() {
  const abierto = useUiStore((s) => s.gastoRapidoAbierto);
  const setAbierto = useUiStore((s) => s.setGastoRapidoAbierto);
  const { data: cuentas } = useCuentas();
  const crear = useCrearGasto();

  const [monto, setMonto] = useState("");
  const [categoria, setCategoria] = useState<string>(CATEGORIAS[0]);
  const [cuentaId, setCuentaId] = useState<number | null>(null);
  const [nota, setNota] = useState("");

  useEffect(() => {
    if (cuentas?.length && cuentaId === null) {
      setCuentaId((cuentas.find((c) => c.es_principal) ?? cuentas[0]).id);
    }
  }, [cuentas, cuentaId]);

  useEffect(() => {
    if (!abierto) {
      setMonto("");
      setNota("");
      crear.reset();
    }
    // crear.reset es estable; solo interesa reaccionar al cierre
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto]);

  if (!abierto) return null;

  const montoValido = Number(monto) > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4"
      onClick={() => setAbierto(false)}
    >
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={(e) => {
          e.preventDefault();
          if (!montoValido || cuentaId === null) return;
          crear.mutate(
            {
              monto,
              categoria,
              cuenta_id: cuentaId,
              ...(nota.trim() ? { descripcion: nota.trim() } : {}),
            },
            { onSuccess: () => setAbierto(false) },
          );
        }}
        className="w-full max-w-lg rounded-t-3xl bg-card p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] shadow-2xl ring-1 ring-[var(--border-ring)] sm:rounded-3xl sm:pb-5"
      >
        <p className="text-lg leading-relaxed">
          Hoy gasté{" "}
          <span className="inline-flex items-baseline rounded-xl bg-page px-2 py-1 ring-1 ring-[var(--border-ring)] focus-within:ring-2 focus-within:ring-accent">
            <span className="text-ink-3">S/</span>
            <input
              autoFocus
              inputMode="decimal"
              value={monto}
              onChange={(e) => setMonto(e.target.value.replace(",", "."))}
              placeholder="0.00"
              size={5}
              className="w-20 bg-transparent px-1 text-lg font-semibold text-ink outline-none placeholder:text-ink-3"
            />
          </span>{" "}
          en{" "}
          <select
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
            className="touch-44 rounded-xl bg-page px-2 text-base text-ink ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
          >
            {CATEGORIAS.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>{" "}
          pagando con{" "}
          <select
            value={cuentaId ?? ""}
            onChange={(e) => setCuentaId(Number(e.target.value))}
            className="touch-44 rounded-xl bg-page px-2 text-base text-ink ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
          >
            {(cuentas ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
          .
        </p>

        <input
          value={nota}
          onChange={(e) => setNota(e.target.value)}
          placeholder="Nota (opcional)"
          maxLength={300}
          className="mt-4 w-full touch-44 rounded-xl bg-page px-3 text-sm text-ink ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
        />

        {crear.isError && (
          <p role="alert" className="mt-3 text-sm text-critical">
            No se pudo registrar el gasto.
          </p>
        )}

        <div className="mt-5 flex gap-2">
          <Boton
            type="button"
            variante="secundario"
            className="flex-1"
            onClick={() => setAbierto(false)}
          >
            Cancelar
          </Boton>
          <Boton type="submit" className="flex-1" disabled={!montoValido || crear.isPending}>
            {crear.isPending ? "Guardando…" : "Registrar"}
          </Boton>
        </div>
      </form>
    </div>
  );
}
