import {
  Bell,
  CalendarClock,
  CreditCard,
  LayoutGrid,
  LogOut,
  Menu,
  PiggyBank,
  Plus,
  Settings,
  Target,
  Wallet,
  WalletCards,
  X,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { prefetchRuta } from "@/api/prefetch";
import { useLogout, useMe } from "@/api/queries";
import { MenuCuenta, SelectorTema } from "@/components/layout/MenuCuenta";
import { cn } from "@/lib/cn";
import { useUiStore } from "@/stores/uiStore";

const NAV = [
  { to: "/", icono: LayoutGrid, etiqueta: "Panel" },
  { to: "/movimientos", icono: WalletCards, etiqueta: "Movimientos" },
  { to: "/cuentas", icono: Wallet, etiqueta: "Cuentas" },
  { to: "/presupuestos", icono: Target, etiqueta: "Presupuestos" },
  { to: "/deudas", icono: CreditCard, etiqueta: "Deudas" },
  { to: "/ahorros", icono: PiggyBank, etiqueta: "Ahorros" },
  { to: "/recurrentes", icono: CalendarClock, etiqueta: "Recurrentes" },
];

/** En la barra inferior del móvil entran dos a cada lado del FAB. */
const TAB_BAR = [NAV[0], NAV[1]];
const TAB_BAR_DER = [NAV[4]];

export function AppShell({ children }: { children: ReactNode }) {
  const abrirCaptura = useUiStore((s) => s.abrirCaptura);
  const [masAbierto, setMasAbierto] = useState(false);
  const [menuAbierto, setMenuAbierto] = useState(false);
  const logout = useLogout();
  const { data: me } = useMe();
  const qc = useQueryClient();

  const iniciales = (me?.email ?? "?").slice(0, 2).toUpperCase();
  const enMas = NAV.filter((n) => ![...TAB_BAR, ...TAB_BAR_DER].includes(n));

  return (
    <div className="min-h-dvh lg:flex">
      {/* ── Sidebar (desktop) ── */}
      <aside className="hidden w-[268px] shrink-0 flex-col border-r border-hairline bg-card px-4 py-5 lg:flex">
        <div className="flex items-center gap-3 px-2">
          <span className="flex size-9 items-center justify-center rounded-xl bg-accent text-white">
            <WalletCards size={18} />
          </span>
          <span className="text-lg font-bold tracking-tight">Fondo</span>
        </div>

        <p className="mt-7 px-3 text-[11px] font-semibold tracking-[0.08em] text-ink-3">
          GENERAL
        </p>

        <nav className="mt-2 space-y-1">
          {NAV.map(({ to, icono: Icono, etiqueta }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              // Precarga al pasar el cursor: al soltar el clic los datos ya están
              onMouseEnter={() => prefetchRuta(qc, to)}
              onFocus={() => prefetchRuta(qc, to)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-medium transition-colors",
                  isActive
                    ? "bg-accent-soft text-accent-ink"
                    : "text-ink-2 hover:bg-card-soft hover:text-ink",
                )
              }
            >
              <Icono size={19} />
              {etiqueta}
            </NavLink>
          ))}
        </nav>

        {/* Pie: usuario + ajustes */}
        <div className="relative mt-auto pt-4">
          {menuAbierto && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setMenuAbierto(false)}
                aria-hidden
              />
              <div className="absolute bottom-full left-2 z-50 mb-2">
                <MenuCuenta onCerrar={() => setMenuAbierto(false)} />
              </div>
            </>
          )}

          <div className="flex items-center gap-3 px-2">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-bold text-accent-ink">
              {iniciales}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold">
                {me?.email?.split("@")[0] ?? "Mi cuenta"}
              </span>
              <span className="block truncate text-xs text-ink-3">{me?.email}</span>
            </span>
            <button
              onClick={() => setMenuAbierto((v) => !v)}
              aria-label="Ajustes de la cuenta"
              aria-expanded={menuAbierto}
              className={cn(
                "flex size-9 shrink-0 items-center justify-center rounded-lg transition-colors",
                menuAbierto
                  ? "bg-card-soft text-ink"
                  : "text-ink-3 hover:bg-card-soft hover:text-ink",
              )}
            >
              <Settings size={17} />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Contenido ── */}
      <div className="min-w-0 flex-1 pb-28 lg:pb-0">
        <main className="px-4 py-3 lg:px-8 lg:py-6">{children}</main>
      </div>

      {/* ── Tab bar (móvil) con FAB central ── */}
      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-hairline bg-card pb-[env(safe-area-inset-bottom)] lg:hidden">
        <div className="grid grid-cols-5 items-center">
          {TAB_BAR.map(({ to, icono: Icono, etiqueta }) => (
            <ItemTab key={to} to={to} Icono={Icono} etiqueta={etiqueta} />
          ))}

          {/* Hueco central: el FAB flota por encima */}
          <div aria-hidden />

          {TAB_BAR_DER.map(({ to, icono: Icono, etiqueta }) => (
            <ItemTab key={to} to={to} Icono={Icono} etiqueta={etiqueta} />
          ))}
          <button
            onClick={() => setMasAbierto(true)}
            className="flex touch-44 flex-col items-center justify-center gap-1 py-2.5 text-[11px] font-medium text-ink-3"
          >
            <Menu size={22} />
            Más
          </button>
        </div>
      </nav>

      <button
        aria-label="Nuevo movimiento"
        onClick={() => abrirCaptura("gasto")}
        className="fixed bottom-[calc(1.15rem+env(safe-area-inset-bottom))] left-1/2 z-40 flex size-16 -translate-x-1/2 items-center justify-center rounded-full bg-accent text-white shadow-[0_8px_24px_rgba(91,79,232,0.45)] transition-colors hover:bg-accent-hover lg:bottom-8 lg:left-auto lg:right-8 lg:size-14 lg:translate-x-0"
      >
        <Plus size={26} />
      </button>

      {/* Hoja «Más» */}
      {masAbierto && (
        <div
          className="fixed inset-0 z-50 flex items-end bg-black/40 lg:hidden"
          onClick={() => setMasAbierto(false)}
        >
          <div
            role="dialog"
            aria-label="Más secciones"
            onClick={(e) => e.stopPropagation()}
            className="w-full rounded-t-2xl bg-card p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] shadow-2xl"
          >
            <div aria-hidden className="mx-auto mb-3 h-1 w-9 rounded-full bg-hairline" />
            <div className="flex items-center">
              <h2 className="font-bold">Más</h2>
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
                      "flex items-center gap-3 rounded-xl px-3 py-3 text-[15px] font-medium",
                      isActive ? "bg-accent-soft text-accent-ink" : "text-ink-2",
                    )
                  }
                >
                  <Icono size={19} />
                  {etiqueta}
                </NavLink>
              ))}
            </nav>

            <div className="mt-3 border-t border-hairline pt-3">
              <SelectorTema />
              <button
                onClick={() => logout.mutate()}
                className="mt-2 flex w-full items-center gap-3 rounded-xl px-3 py-3 text-[15px] font-medium text-ink-2"
              >
                <LogOut size={19} />
                Cerrar sesión
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ItemTab({
  to,
  Icono,
  etiqueta,
}: {
  to: string;
  Icono: typeof LayoutGrid;
  etiqueta: string;
}) {
  const qc = useQueryClient();
  return (
    <NavLink
      to={to}
      end={to === "/"}
      // En táctil el prefetch arranca al apoyar el dedo, antes del click
      onTouchStart={() => prefetchRuta(qc, to)}
      className={({ isActive }) =>
        cn(
          "flex touch-44 flex-col items-center justify-center gap-1 py-2.5 text-[11px] font-medium",
          isActive ? "text-accent" : "text-ink-3",
        )
      }
    >
      <Icono size={22} />
      {etiqueta}
    </NavLink>
  );
}

/** Cabecera móvil: título, subtítulo, campana y avatar (mockup). */
export function HeaderMovil({
  titulo,
  subtitulo,
}: {
  titulo: string;
  subtitulo?: string;
}) {
  const { data: me } = useMe();
  const iniciales = (me?.email ?? "?").slice(0, 2).toUpperCase();
  return (
    <header className="flex items-start gap-3 pb-4 lg:hidden">
      <div className="min-w-0 flex-1">
        <h1 className="text-2xl font-bold tracking-tight">{titulo}</h1>
        {subtitulo && <p className="mt-0.5 text-sm text-ink-2">{subtitulo}</p>}
      </div>
      <button
        aria-label="Notificaciones"
        className="flex size-10 shrink-0 items-center justify-center rounded-full bg-card shadow-sm ring-1 ring-[var(--ring)]"
      >
        <Bell size={18} className="text-ink-2" />
      </button>
      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-bold text-accent-ink">
        {iniciales}
      </span>
    </header>
  );
}
