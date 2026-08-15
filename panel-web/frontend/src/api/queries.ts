import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type { Cuenta, DashboardResumen, Me, MovimientosPage } from "./types";

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

export function useCrearGasto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      monto: string;
      categoria: string;
      cuenta_id: number;
      descripcion?: string;
      medio?: string;
    }) => api("/gastos", { method: "POST", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["movimientos"] });
    },
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
