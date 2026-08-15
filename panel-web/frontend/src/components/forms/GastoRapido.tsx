import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";

import { useCrearGasto, useCuentas } from "@/api/queries";
import { CATEGORIAS } from "@/api/types";
import { Boton } from "@/components/ui/Boton";
import { useUiStore } from "@/stores/uiStore";

/** Slot inline del Mad Libs: misma altura (44px táctil), mismo radio y alineación
 *  para que la frase se lea como texto y no como un formulario desalineado. */
const SLOT =
  "inline-flex h-11 items-center rounded-xl bg-page align-middle ring-1 ring-[var(--border-ring)] focus-within:ring-2 focus-within:ring-accent";

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
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4"
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
        {/* leading-[3rem] da aire vertical para que los slots de 44px no se apiñen al envolver */}
        <p className="text-lg leading-[3rem]">
          Hoy gasté{" "}
          <span className={`${SLOT} px-3`}>
            <span className="text-base text-ink-3">S/</span>
            <input
              autoFocus
              inputMode="decimal"
              value={monto}
              onChange={(e) => setMonto(e.target.value.replace(",", "."))}
              placeholder="0.00"
              className="w-[4.5rem] bg-transparent pl-1.5 text-lg font-semibold text-ink outline-none placeholder:font-normal placeholder:text-ink-3"
            />
          </span>{" "}
          en <Selector valor={categoria} onChange={setCategoria} opciones={CATEGORIAS} />{" "}
          pagando con{" "}
          <Selector
            valor={String(cuentaId ?? "")}
            onChange={(v) => setCuentaId(Number(v))}
            opciones={(cuentas ?? []).map((c) => ({ valor: String(c.id), etiqueta: c.nombre }))}
          />
        </p>

        <input
          value={nota}
          onChange={(e) => setNota(e.target.value)}
          placeholder="Nota (opcional)"
          maxLength={300}
          className="mt-4 h-11 w-full rounded-xl bg-page px-3 text-sm text-ink ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
        />

        {crear.isError && (
          <p role="alert" className="mt-3 text-sm text-critical">
            No se pudo registrar el gasto.
          </p>
        )}

        <div className="mt-5 flex gap-3">
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

type Opcion = { valor: string; etiqueta: string };

/** Select nativo (mejor UX táctil) envuelto para controlar altura y flecha. */
function Selector({
  valor,
  onChange,
  opciones,
}: {
  valor: string;
  onChange: (v: string) => void;
  opciones: readonly string[] | Opcion[];
}) {
  const items: Opcion[] = opciones.map((o) =>
    typeof o === "string" ? { valor: o, etiqueta: o } : o,
  );
  return (
    <span className={`${SLOT} relative pl-3 pr-8`}>
      <select
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-transparent text-base text-ink outline-none"
      >
        {items.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.etiqueta}
          </option>
        ))}
      </select>
      <ChevronDown
        size={16}
        aria-hidden
        className="pointer-events-none absolute right-2.5 text-ink-3"
      />
    </span>
  );
}
