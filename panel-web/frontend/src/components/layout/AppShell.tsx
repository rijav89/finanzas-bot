import { LayoutDashboard, ListOrdered, LogOut, Minus, Plus, Search, Wallet, X } from "lucide-react";
import { useState, type ReactNode } from "react";
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
  const [fabAbierto, setFabAbierto] = useState(false);
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

      {/* FAB expandible: gasto o ingreso, como el menú del bot */}
      {fabAbierto && (
        <div
          className="fixed inset-0 z-30 bg-black/20"
          onClick={() => setFabAbierto(false)}
          aria-hidden
        />
      )}
      <div className="fixed bottom-20 right-4 z-40 flex flex-col items-end gap-3 lg:bottom-8 lg:right-8">
        {fabAbierto && (
          <>
            <AccionFab
              etiqueta="Ingreso"
              icono={Plus}
              clase="bg-good-text"
              onClick={() => {
                setFabAbierto(false);
                abrirCaptura("ingreso");
              }}
            />
            <AccionFab
              etiqueta="Gasto"
              icono={Minus}
              clase="bg-accent"
              onClick={() => {
                setFabAbierto(false);
                abrirCaptura("gasto");
              }}
            />
          </>
        )}
        <button
          aria-label={fabAbierto ? "Cerrar acciones" : "Registrar movimiento"}
          aria-expanded={fabAbierto}
          onClick={() => setFabAbierto((v) => !v)}
          className={cn(
            "flex size-14 items-center justify-center rounded-full text-white shadow-lg transition-transform",
            fabAbierto ? "bg-ink-3 rotate-90" : "bg-accent",
          )}
        >
          {fabAbierto ? <X size={24} /> : <Plus size={24} />}
        </button>
      </div>
    </div>
  );
}

function AccionFab({
  etiqueta,
  icono: Icono,
  clase,
  onClick,
}: {
  etiqueta: string;
  icono: typeof Plus;
  clase: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 rounded-full bg-card py-1.5 pl-4 pr-1.5 shadow-lg ring-1 ring-[var(--border-ring)]"
    >
      <span className="text-sm font-medium">{etiqueta}</span>
      <span className={cn("flex size-11 items-center justify-center rounded-full text-white", clase)}>
        <Icono size={20} />
      </span>
    </button>
  );
}
