import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { useMe } from "@/api/queries";
import { CommandPalette } from "@/components/command/CommandPalette";
import { GastoRapido } from "@/components/forms/GastoRapido";
import { AppShell } from "@/components/layout/AppShell";

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Movimientos = lazy(() => import("@/pages/Movimientos"));
const Cuentas = lazy(() => import("@/pages/Cuentas"));
const Login = lazy(() => import("@/pages/Login"));
const Vincular = lazy(() => import("@/pages/Vincular"));

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } },
});

function Cargando() {
  return (
    <div className="flex min-h-dvh items-center justify-center">
      <div className="size-8 animate-spin rounded-full border-2 border-hairline border-t-accent" />
    </div>
  );
}

/** Decide qué ve el usuario: login → vinculación → app. */
function Ruteador() {
  const { data: me, isPending, isError } = useMe();

  if (isPending) return <Cargando />;
  // 401 (sin sesión) llega como error del query
  if (isError || !me) {
    return (
      <Suspense fallback={<Cargando />}>
        <Login />
      </Suspense>
    );
  }
  if (!me.vinculado) {
    return (
      <Suspense fallback={<Cargando />}>
        <Vincular />
      </Suspense>
    );
  }

  return (
    <AppShell>
      <Suspense fallback={<Cargando />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/movimientos" element={<Movimientos />} />
          <Route path="/cuentas" element={<Cuentas />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </Suspense>
      <CommandPalette />
      <GastoRapido />
    </AppShell>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Ruteador />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
