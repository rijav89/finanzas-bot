import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { useMe } from "@/api/queries";
import { CommandPalette } from "@/components/command/CommandPalette";
import { CapturaRapida } from "@/components/forms/CapturaRapida";
import { AppShell } from "@/components/layout/AppShell";

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Movimientos = lazy(() => import("@/pages/Movimientos"));
const Cuentas = lazy(() => import("@/pages/Cuentas"));
const Presupuestos = lazy(() => import("@/pages/Presupuestos"));
const Deudas = lazy(() => import("@/pages/Deudas"));
const DeudaDetalle = lazy(() => import("@/pages/DeudaDetalle"));
const Ahorros = lazy(() => import("@/pages/Ahorros"));
const Recurrentes = lazy(() => import("@/pages/Recurrentes"));
const Login = lazy(() => import("@/pages/Login"));
const Vincular = lazy(() => import("@/pages/Vincular"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      // Cada request cuesta ~180 ms contra Supabase: mantener los datos "frescos"
      // un rato hace que volver a una sección ya vista sea instantáneo.
      staleTime: 2 * 60_000,
      gcTime: 30 * 60_000,
      // Al cambiar de filtro/mes conserva lo anterior mientras llega lo nuevo,
      // en vez de parpadear a esqueleto.
      placeholderData: (previo: unknown) => previo,
    },
  },
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
          <Route path="/presupuestos" element={<Presupuestos />} />
          <Route path="/deudas" element={<Deudas />} />
          <Route path="/deudas/:id" element={<DeudaDetalle />} />
          <Route path="/ahorros" element={<Ahorros />} />
          <Route path="/recurrentes" element={<Recurrentes />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </Suspense>
      <CommandPalette />
      <CapturaRapida />
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
