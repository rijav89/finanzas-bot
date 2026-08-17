import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Tema = "claro" | "oscuro" | "sistema";

/** El CSS define: :root = claro · [data-theme="dark"] = oscuro forzado ·
 *  [data-theme="light"] = claro forzado · sin atributo = lo que diga el sistema. */
function aplicar(tema: Tema): void {
  const el = document.documentElement;
  if (tema === "sistema") {
    el.removeAttribute("data-theme");
  } else {
    el.setAttribute("data-theme", tema === "oscuro" ? "dark" : "light");
  }
  // La barra del navegador en móvil sigue al tema activo
  const oscuro =
    tema === "oscuro" ||
    (tema === "sistema" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", oscuro ? "#0b0c0f" : "#f6f7f9");
}

interface TemaState {
  tema: Tema;
  setTema: (t: Tema) => void;
}

export const useTemaStore = create<TemaState>()(
  persist(
    (set) => ({
      tema: "sistema",
      setTema: (tema) => {
        aplicar(tema);
        set({ tema });
      },
    }),
    {
      name: "finanzas-tema",
      // Al volver a entrar, reaplica lo que el usuario había elegido
      onRehydrateStorage: () => (estado) => estado && aplicar(estado.tema),
    },
  ),
);

/** Mantiene sincronizada la barra del navegador cuando el tema es "sistema"
 *  y el usuario cambia el modo del SO. */
export function escucharTemaDelSistema(): () => void {
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  const alCambiar = () => {
    if (useTemaStore.getState().tema === "sistema") aplicar("sistema");
  };
  mq.addEventListener("change", alCambiar);
  return () => mq.removeEventListener("change", alCambiar);
}
