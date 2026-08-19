import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type {
  Ahorro,
  Categoria,
  Cuenta,
  Cuota,
  DashboardResumen,
  Deuda,
  DeudasResp,
  InsightsResp,
  Me,
  MovimientosPage,
  PresupuestosResp,
  Recurrente,
} from "./types";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api<Me>("/auth/me"),
    retry: false,
    staleTime: 5 * 60_000,
  });
}

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api<DashboardResumen>("/dashboard/resumen"),
    staleTime: 60_000,
  });
}

export function useCuentas() {
  return useQuery({
    queryKey: ["cuentas"],
    queryFn: () => api<Cuenta[]>("/cuentas"),
    staleTime: 5 * 60_000,
  });
}

export function useMovimientos(filtros: { q?: string; tipo?: string } = {}) {
  const params = new URLSearchParams();
  if (filtros.q) params.set("q", filtros.q);
  if (filtros.tipo) params.set("tipo", filtros.tipo);
  const qs = params.toString();
  return useQuery({
    queryKey: ["movimientos", filtros],
    queryFn: () => api<MovimientosPage>(`/movimientos${qs ? `?${qs}` : ""}`),
    staleTime: 30_000,
  });
}

export interface MovimientoNuevo {
  monto: string;
  categoria: string;
  cuenta_id: number;
  descripcion?: string;
  /** YYYY-MM-DD; el backend usa hoy si se omite. */
  fecha?: string;
}

/** Crea gasto o ingreso según `tipo`; ambos invalidan dashboard + historial. */
export function useCrearMovimiento() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ tipo, ...body }: MovimientoNuevo & { tipo: "gasto" | "ingreso" }) =>
      api(tipo === "gasto" ? "/gastos" : "/ingresos", { method: "POST", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["movimientos"] });
    },
  });
}

// ── Módulos F4 ───────────────────────────────────────────────────────────────

/** Invalida todo lo que cambia cuando se toca dinero (dashboard, historial, módulos). */
function useInvalidarFinanzas() {
  const qc = useQueryClient();
  return () => {
    for (const k of ["dashboard", "movimientos", "deudas", "ahorros", "presupuestos"]) {
      qc.invalidateQueries({ queryKey: [k] });
    }
  };
}

export function useCrearCuenta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      nombre: string;
      tipo: "corriente" | "ahorro";
      saldo_inicial: string;
    }) => api("/cuentas", { method: "POST", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cuentas"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useEditarCuenta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; nombre?: string; tipo?: string }) =>
      api(`/cuentas/${id}`, { method: "PATCH", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cuentas"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["ahorros"] });
    },
  });
}

export function useArchivarCuenta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api(`/cuentas/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["cuentas"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useEliminarMovimiento() {
  const invalidar = useInvalidarFinanzas();
  return useMutation({
    mutationFn: ({ tipo, id }: { tipo: "gastos" | "ingresos"; id: number }) =>
      api(`/${tipo}/${id}`, { method: "DELETE" }),
    onSuccess: invalidar,
  });
}

export function useCategorias(
  opciones: { tipo?: "gasto" | "ingreso"; incluirArchivadas?: boolean } = {},
) {
  const { tipo, incluirArchivadas } = opciones;
  const qs = new URLSearchParams();
  if (tipo) qs.set("tipo", tipo);
  if (incluirArchivadas) qs.set("incluir_archivadas", "true");
  const sufijo = qs.toString() ? `?${qs}` : "";

  return useQuery({
    queryKey: ["categorias", tipo ?? "todas", incluirArchivadas ?? false],
    queryFn: () => api<Categoria[]>(`/categorias${sufijo}`),
    staleTime: 10 * 60_000,
  });
}

function invalidarCategorias(qc: ReturnType<typeof useQueryClient>) {
  // Renombrar arrastra los movimientos, así que el dashboard y el historial cambian
  for (const key of [["categorias"], ["dashboard"], ["movimientos"]])
    void qc.invalidateQueries({ queryKey: key });
}

export function useCrearCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { nombre: string; tipo: "gasto" | "ingreso"; color?: string; icono?: string }) =>
      api<Categoria>("/categorias", { method: "POST", body }),
    onSuccess: () => invalidarCategorias(qc),
  });
}

export function useEditarCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...body
    }: { id: number; nombre?: string; color?: string; icono?: string; activa?: boolean }) =>
      api<Categoria>(`/categorias/${id}`, { method: "PATCH", body }),
    onSuccess: () => invalidarCategorias(qc),
  });
}

export function useArchivarCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api(`/categorias/${id}`, { method: "DELETE" }),
    onSuccess: () => invalidarCategorias(qc),
  });
}

export function usePresupuestos(anio?: number, mes?: number) {
  const qs = anio && mes ? `?anio=${anio}&mes=${mes}` : "";
  return useQuery({
    queryKey: ["presupuestos", anio, mes],
    queryFn: () => api<PresupuestosResp>(`/presupuestos${qs}`),
    staleTime: 60_000,
  });
}

export function useGuardarPresupuestos() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      anio: number;
      mes: number;
      items: { categoria: string; monto_limite: string }[];
    }) => api("/presupuestos", { method: "PUT", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["presupuestos"] }),
  });
}

export function useDeudas() {
  return useQuery({
    queryKey: ["deudas"],
    queryFn: () => api<DeudasResp>("/deudas"),
    staleTime: 60_000,
  });
}

export function useDeuda(id: number | null) {
  return useQuery({
    queryKey: ["deudas", id],
    queryFn: () => api<Deuda & { cuotas: Cuota[] }>(`/deudas/${id}`),
    enabled: id !== null,
  });
}

export function useCrearDeuda() {
  // Crear puede mover plata (el desembolso), así que se invalida todo lo financiero
  const invalidar = useInvalidarFinanzas();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api("/deudas", { method: "POST", body }),
    onSuccess: invalidar,
  });
}

/** Devolución parcial o total de un préstamo sin cronograma. */
export function useRegistrarMovimientoDeuda() {
  const invalidar = useInvalidarFinanzas();
  return useMutation({
    mutationFn: ({
      deudaId,
      ...body
    }: {
      deudaId: number;
      monto: string;
      cuenta_id?: number;
      fecha?: string;
    }) => api(`/deudas/${deudaId}/movimientos`, { method: "POST", body }),
    onSuccess: invalidar,
  });
}

export function usePagarCuota() {
  const invalidar = useInvalidarFinanzas();
  return useMutation({
    mutationFn: ({
      deudaId,
      numero,
      cuenta_id,
    }: {
      deudaId: number;
      numero: number;
      cuenta_id?: number;
    }) =>
      api(`/deudas/${deudaId}/cuotas/${numero}/pagar`, {
        method: "POST",
        body: cuenta_id ? { cuenta_id } : {},
      }),
    onSuccess: invalidar,
  });
}

export function useInsights() {
  return useQuery({
    queryKey: ["insights"],
    queryFn: () => api<InsightsResp>("/insights"),
    // Los genera un cron semanal: no tiene sentido revalidarlos seguido
    staleTime: 30 * 60_000,
  });
}

export function useMarcarInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api(`/insights/${id}`, { method: "PATCH", body: { leido: true } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["insights"] }),
  });
}

export function useAhorros() {
  return useQuery({
    queryKey: ["ahorros"],
    queryFn: () => api<{ items: Ahorro[]; total_ahorrado: number }>("/ahorros"),
    staleTime: 60_000,
  });
}

export function useDefinirMetaAhorro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      cuentaId,
      ...body
    }: {
      cuentaId: number;
      monto_objetivo: string;
      fecha_objetivo?: string | null;
    }) => api(`/ahorros/${cuentaId}/meta`, { method: "PUT", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ahorros"] });
      qc.invalidateQueries({ queryKey: ["cuentas"] });
    },
  });
}

export function useRecurrentes() {
  return useQuery({
    queryKey: ["recurrentes"],
    queryFn: () =>
      api<{ items: Recurrente[]; total_mensual: number }>("/recurrentes"),
    staleTime: 60_000,
  });
}

export function useCrearRecurrente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api("/recurrentes", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recurrentes"] }),
  });
}

export function useEditarRecurrente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number } & Record<string, unknown>) =>
      api(`/recurrentes/${id}`, { method: "PATCH", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recurrentes"] }),
  });
}

export function useEliminarRecurrente() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api(`/recurrentes/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recurrentes"] }),
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      api("/auth/login", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useVincular() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { codigo: string }) =>
      api("/auth/vincular", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api("/auth/logout", { method: "POST", body: {} }),
    onSuccess: () => qc.clear(),
  });
}
