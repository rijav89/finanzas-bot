import { create } from "zustand";
import { persist } from "zustand/middleware";

export const WIDGETS_DEFAULT = [
  "saldo-total",
  "ingresos",
  "gastos",
  "tendencia-saldo",
  "ultimos-registros",
  "insights",
] as const;

export type WidgetId = (typeof WIDGETS_DEFAULT)[number];

interface BentoState {
  orden: WidgetId[];
  setOrden: (orden: WidgetId[]) => void;
}

export const useBentoStore = create<BentoState>()(
  persist(
    (set) => ({
      orden: [...WIDGETS_DEFAULT],
      setOrden: (orden) => set({ orden }),
    }),
    {
      name: "finanzas-bento",
      // v2 rehízo el tablero entero (flujo y categorías se fusionaron en ingresos y
      // gastos): conservar el orden viejo dejaría las tarjetas nuevas al final.
      version: 2,
      migrate: () => ({ orden: [...WIDGETS_DEFAULT] }),
      // Si más adelante se agrega un widget suelto, se fusiona con el orden guardado
      merge: (persisted, current) => {
        const p = persisted as Partial<BentoState> | undefined;
        const guardado = p?.orden ?? [];
        const faltantes = WIDGETS_DEFAULT.filter((w) => !guardado.includes(w));
        return {
          ...current,
          orden: [...guardado.filter((w) => WIDGETS_DEFAULT.includes(w)), ...faltantes],
        };
      },
    },
  ),
);
