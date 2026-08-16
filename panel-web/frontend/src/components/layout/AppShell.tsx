import {
  CalendarClock,
  Landmark,
  LayoutDashboard,
  ListOrdered,
  LogOut,
  MoreHorizontal,
  PiggyBank,
  Plus,
  Search,
  Wallet,
  X,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useLogout } from "@/api/queries";
import { cn } from "@/lib/cn";
import { useUiStore } from "@/stores/uiStore";

/** Navegación completa. `enTabBar` marca lo que va en la barra inferior del móvil;
 *  el resto vive detrás de «Más» para no apretar los toques. */
const NAV = [
  { to: "/", icono: LayoutDashboard, etiqueta: "Panel", enTabBar: true },
  { to: "/movimientos", icono: ListOrdered, etiqueta: "Movimientos", enTabBar: true },
  { to: "/cuentas", icono: Wallet, etiqueta: "Cuentas", enTabBar: true },
  { to: "/presupuestos", icono: LayoutDashboard, etiqueta: "Presupuestos", enTabBar: false },
  { to: "/deudas", icono: Landmark, etiqueta: "Deudas", enTabBar: false },
  { to: "/ahorros", icono: PiggyBank, etiqueta: "Ahorros", enTabBar: false },
  { to: "/recurrentes", icono: CalendarClock, etiqueta: "Recurrentes", enTabBar: false },
];

export function AppShell({ children }: { children: ReactNode }) {
  const setPaleta = useUiStore((s) => s.setPaletaAbierta);
  const abrirCaptura = useUiStore((s) => s.abrirCaptura);
  const [masAbierto, setMasAbierto] = useState(false);
  const logout = useLogout();

  const enTabBar = NAV.filter((n) => n.enTabBar);
  const enMas = NAV.filter((n) => !n.enTabBar);

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
        {/* Header móvil — compacto para dejar el alto a los datos */}
        <header className="flex items-center gap-2 px-4 py-2.5 lg:hidden">
          <span className="text-base font-semibold">FinanzasBot</span>
          <button
            aria-label="Buscar"
            onClick={() => setPaleta(true)}
            className="ml-auto flex size-10 items-center justify-center rounded-xl bg-card ring-1 ring-[var(--border-ring)]"
          >
            <Search size={18} className="text-ink-2" />
          </button>
        </header>

        <main className="px-4 lg:p-8">{children}</main>
      </div>

      {/* Tab bar — solo móvil */}
      <nav className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around border-t border-hairline bg-card pb-[env(safe-area-inset-bottom)] lg:hidden">
        {enTabBar.map(({ to, icono: Icono, etiqueta }) => (
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
        <button
          onClick={() => setMasAbierto(true)}
          className="flex touch-44 flex-1 flex-col items-center justify-center gap-0.5 py-2 text-[11px] text-ink-3"
        >
          <MoreHorizontal size={20} />
          Más
        </button>
      </nav>

      {/* Hoja «Más» — el resto de secciones en móvil */}
      {masAbierto && (
        <div
          className="fixed inset-0 z-50 flex items-end bg-black/50 lg:hidden"
          onClick={() => setMasAbierto(false)}
        >
          <div
            role="dialog"
            aria-label="Más secciones"
            onClick={(e) => e.stopPropagation()}
            className="w-full rounded-t-2xl bg-card p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] shadow-2xl"
          >
            <div className="flex items-center">
              <h2 className="font-semibold">Más</h2>
              <button
                onClick={() => setMasAbierto(false)}
                aria-label="Cerrar"
                className="ml-auto flex size-9 items-center justify-center rounded-lg text-ink-3"
              >
                <X size={18} />
              </button>
            </div>
            <nav className="mt-2 space-y-1">
              {enMas.map(({ to, icono: Icono, etiqueta }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={() => setMasAbierto(false)}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-xl px-3 py-3 text-sm",
                      isActive ? "bg-page text-ink" : "text-ink-2",
                    )
                  }
                >
                  <Icono size={18} />
                  {etiqueta}
                </NavLink>
              ))}
              <button
                onClick={() => logout.mutate()}
                className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm text-ink-2"
              >
                <LogOut size={18} />
                Salir
              </button>
            </nav>
          </div>
        </div>
      )}

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
