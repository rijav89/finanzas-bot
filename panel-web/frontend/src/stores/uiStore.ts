import { create } from "zustand";

export type TipoMovimiento = "gasto" | "ingreso";

interface UiState {
  paletaAbierta: boolean;
  setPaletaAbierta: (v: boolean) => void;
  /** null = cerrado; si no, indica con qué pestaña abre la captura rápida. */
  captura: TipoMovimiento | null;
  abrirCaptura: (tipo?: TipoMovimiento) => void;
  cerrarCaptura: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  paletaAbierta: false,
  setPaletaAbierta: (v) => set({ paletaAbierta: v }),
  captura: null,
  abrirCaptura: (tipo = "gasto") => set({ captura: tipo }),
  cerrarCaptura: () => set({ captura: null }),
}));
