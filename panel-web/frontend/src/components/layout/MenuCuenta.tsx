import { LogOut, Monitor, Moon, Settings, Sun } from "lucide-react";
import { Link } from "react-router-dom";

import { useLogout, useMe } from "@/api/queries";
import { cn } from "@/lib/cn";
import { useTemaStore, type Tema } from "@/stores/temaStore";

const OPCIONES: { valor: Tema; etiqueta: string; Icono: typeof Sun }[] = [
  { valor: "claro", etiqueta: "Claro", Icono: Sun },
  { valor: "oscuro", etiqueta: "Oscuro", Icono: Moon },
  { valor: "sistema", etiqueta: "Sistema", Icono: Monitor },
];

/** Selector de tema: tres opciones, la activa resaltada. */
export function SelectorTema() {
  const tema = useTemaStore((s) => s.tema);
  const setTema = useTemaStore((s) => s.setTema);

  return (
    <div>
      <p className="mb-1.5 px-1 text-xs font-semibold text-ink-3">Tema</p>
      <div
        role="radiogroup"
        aria-label="Tema de la interfaz"
        className="flex gap-1 rounded-xl bg-card-soft p-1"
      >
        {OPCIONES.map(({ valor, etiqueta, Icono }) => {
          const activo = tema === valor;
          return (
            <button
              key={valor}
              type="button"
              role="radio"
              aria-checked={activo}
              onClick={() => setTema(valor)}
              title={etiqueta}
              className={cn(
                "flex h-10 flex-1 items-center justify-center gap-1.5 rounded-lg text-xs font-semibold transition-colors",
                activo
                  ? "bg-card text-ink shadow-sm ring-1 ring-[var(--ring)]"
                  : "text-ink-2 hover:text-ink",
              )}
            >
              <Icono size={15} aria-hidden />
              {etiqueta}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** Panel de cuenta que abre el engranaje del sidebar. */
export function MenuCuenta({ onCerrar }: { onCerrar: () => void }) {
  const logout = useLogout();
  const { data: me } = useMe();

  return (
    <div
      role="menu"
      className="w-[15.5rem] rounded-2xl bg-card p-3 shadow-xl ring-1 ring-[var(--ring)]"
    >
      <p className="truncate px-1 pb-2 text-sm font-semibold">{me?.email}</p>

      <SelectorTema />

      <div className="my-2 border-t border-hairline" />

      <Link
        to="/configuracion"
        onClick={onCerrar}
        className="flex h-11 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium text-ink-2 transition-colors hover:bg-card-soft hover:text-ink"
      >
        <Settings size={17} />
        Configuración
      </Link>

      <button
        onClick={() => {
          onCerrar();
          logout.mutate();
        }}
        className="flex h-11 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium text-ink-2 transition-colors hover:bg-card-soft hover:text-ink"
      >
        <LogOut size={17} />
        Cerrar sesión
      </button>
    </div>
  );
}
