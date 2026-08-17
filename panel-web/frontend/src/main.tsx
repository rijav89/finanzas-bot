import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./index.css";
import { escucharTemaDelSistema, useTemaStore } from "./stores/temaStore";

// Aplica el tema guardado antes del primer render para evitar un parpadeo.
// (zustand/persist rehidrata de forma síncrona desde localStorage.)
useTemaStore.getState().setTema(useTemaStore.getState().tema);
escucharTemaDelSistema();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
