import { create } from "zustand";

interface UiState {
  paletaAbierta: boolean;
  setPaletaAbierta: (v: boolean) => void;
  gastoRapidoAbierto: boolean;
  setGastoRapidoAbierto: (v: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  paletaAbierta: false,
  setPaletaAbierta: (v) => set({ paletaAbierta: v }),
  gastoRapidoAbierto: false,
  setGastoRapidoAbierto: (v) => set({ gastoRapidoAbierto: v }),
}));
