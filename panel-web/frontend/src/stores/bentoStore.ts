import { create } from "zustand";
import { persist } from "zustand/middleware";

export const WIDGETS_DEFAULT = [
  "saldo-total",
  "gasto-mes",
  "sankey",
  "categorias",
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
      // Si agregamos widgets nuevos en el futuro, fusionar con el default
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
