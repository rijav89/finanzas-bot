import { LayoutDashboard, ListOrdered, LogOut, Plus, Search, Wallet } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useLogout } from "@/api/queries";
import { cn } from "@/lib/cn";
import { useUiStore } from "@/stores/uiStore";

const NAV = [
  { to: "/", icono: LayoutDashboard, etiqueta: "Panel" },
  { to: "/movimientos", icono: ListOrdered, etiqueta: "Movimientos" },
  { to: "/cuentas", icono: Wallet, etiqueta: "Cuentas" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const setPaleta = useUiStore((s) => s.setPaletaAbierta);
  const abrirCaptura = useUiStore((s) => s.abrirCaptura);
  const logout = useLogout();

  return (
    <div className="min-h-dvh lg:flex">
      {/* Sidebar — solo desktop */}
      <aside className="hidden w-56 shrink-0 flex-col border-r border-hairline p-4 lg:flex">
        <div className="px-2 text-lg font-semibold">FinanzasBot</div>

        <button
          onClick={() => setPaleta(true)}
          className="mt-4 flex w-full items-center gap-2 rounded-xl bg-card px-3 py-2 text-sm text-ink-3 ring-1 ring-[var(--border-ring)] hover:text-ink-2"
        >
          <Search size={16} />
          Buscar…
          <kbd className="ml-auto text-xs text-ink-3">Ctrl K</kbd>
        </button>

        <nav className="mt-4 space-y-1">
          {NAV.map(({ to, icono: Icono, etiqueta }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2 text-sm",
                  isActive ? "bg-card text-ink" : "text-ink-2 hover:text-ink",
                )
              }
            >
              <Icono size={18} />
              {etiqueta}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={() => logout.mutate()}
          className="mt-auto flex items-center gap-3 rounded-xl px-3 py-2 text-sm text-ink-2 hover:text-ink"
        >
          <LogOut size={18} />
          Salir
        </button>
      </aside>

      {/* Contenido */}
      <div className="flex-1 pb-24 lg:pb-0">
        {/* Header móvil */}
        <header className="flex items-center gap-2 p-4 lg:hidden">
          <span className="text-lg font-semibold">FinanzasBot</span>
          <button
            aria-label="Buscar"
            onClick={() => setPaleta(true)}
            className="ml-auto touch-44 rounded-xl bg-card px-3 ring-1 ring-[var(--border-ring)]"
          >
            <Search size={18} className="text-ink-2" />
          </button>
        </header>

        <main className="px-4 lg:p-8">{children}</main>
      </div>

      {/* Tab bar + FAB — solo móvil */}
      <nav className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around border-t border-hairline bg-card pb-[env(safe-area-inset-bottom)] lg:hidden">
        {NAV.map(({ to, icono: Icono, etiqueta }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex touch-44 flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[11px]",
                isActive ? "text-accent" : "text-ink-3",
              )
            }
          >
            <Icono size={20} />
            {etiqueta}
          </NavLink>
        ))}
      </nav>

      {/* Un solo disparador: el tipo (gasto/ingreso) se elige dentro del modal */}
      <button
        aria-label="Registrar movimiento"
        onClick={() => abrirCaptura("gasto")}
        className="fixed bottom-20 right-4 z-30 flex size-14 items-center justify-center rounded-full bg-accent text-white shadow-lg lg:bottom-8 lg:right-8"
      >
        <Plus size={24} />
      </button>
    </div>
  );
}
