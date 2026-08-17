import type { QueryClient } from "@tanstack/react-query";

import { api } from "./client";

/** Lo que necesita cada sección, para precargarlo antes de que el usuario entre. */
const POR_RUTA: Record<string, { key: unknown[]; url: string }[]> = {
  "/": [{ key: ["dashboard"], url: "/dashboard/resumen" }],
  "/movimientos": [{ key: ["movimientos", {}], url: "/movimientos" }],
  "/cuentas": [{ key: ["cuentas"], url: "/cuentas" }],
  "/presupuestos": [{ key: ["categorias", "gasto", false], url: "/categorias?tipo=gasto" }],
  "/deudas": [{ key: ["deudas"], url: "/deudas" }],
  "/ahorros": [
    { key: ["ahorros"], url: "/ahorros" },
    { key: ["cuentas"], url: "/cuentas" },
  ],
  "/recurrentes": [{ key: ["recurrentes"], url: "/recurrentes" }],
  "/configuracion": [
    { key: ["categorias", "gasto", true], url: "/categorias?tipo=gasto&incluir_archivadas=true" },
  ],
};

/** Se dispara al pasar el cursor (o tocar) un enlace de navegación: para cuando
 *  el usuario suelta el clic, los datos ya suelen estar en caché. */
export function prefetchRuta(qc: QueryClient, ruta: string): void {
  for (const { key, url } of POR_RUTA[ruta] ?? []) {
    void qc.prefetchQuery({
      queryKey: key,
      queryFn: () => api(url),
      staleTime: 2 * 60_000,
    });
  }
}
