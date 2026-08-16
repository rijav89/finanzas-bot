import { Command } from "cmdk";
import {
  ArrowDownLeft,
  ArrowUpRight,
  CalendarClock,
  CreditCard,
  LayoutGrid,
  PiggyBank,
  Plus,
  Target,
  Wallet,
  WalletCards,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useMovimientos } from "@/api/queries";
import { IconoTile } from "@/lib/iconos";
import { money } from "@/lib/money";
import { useUiStore } from "@/stores/uiStore";

export function CommandPalette() {
  const abierta = useUiStore((s) => s.paletaAbierta);
  const setAbierta = useUiStore((s) => s.setPaletaAbierta);
  const abrirCaptura = useUiStore((s) => s.abrirCaptura);
  const [busqueda, setBusqueda] = useState("");
  const navigate = useNavigate();

  // Ctrl/Cmd+K en escritorio; en móvil el disparador es el botón del header
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setAbierta(!abierta);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [abierta, setAbierta]);

  const { data } = useMovimientos(busqueda.length >= 2 ? { q: busqueda } : {});
  const resultados = busqueda.length >= 2 ? (data?.items ?? []).slice(0, 6) : [];

  function ir(destino: string) {
    setAbierta(false);
    setBusqueda("");
    navigate(destino);
  }

  if (!abierta) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/45 p-4 pt-[10vh] backdrop-blur-[2px]"
      onClick={() => setAbierta(false)}
    >
      <Command
        label="Paleta de comandos"
        className="mx-auto max-w-lg overflow-hidden rounded-2xl bg-card shadow-2xl ring-1 ring-[var(--ring)]"
        onClick={(e) => e.stopPropagation()}
        shouldFilter={false}
      >
        <Command.Input
          autoFocus
          value={busqueda}
          onValueChange={setBusqueda}
          placeholder="Buscar movimientos o ir a…"
          className="w-full border-b border-hairline bg-transparent px-4 py-4 text-[15px] outline-none placeholder:text-ink-3"
        />
        <Command.List className="max-h-[22rem] overflow-y-auto p-2">
          <Command.Empty className="px-3 py-6 text-center text-sm text-ink-3">
            Sin resultados.
          </Command.Empty>

          {resultados.length > 0 && (
            <Command.Group
              heading="Movimientos"
              className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:text-ink-3"
            >
              {resultados.map((m) => (
                <Command.Item
                  key={`${m.tipo}-${m.id}`}
                  value={`mov-${m.tipo}-${m.id}`}
                  onSelect={() => ir("/movimientos")}
                  className="flex cursor-pointer items-center gap-3 rounded-xl px-2 py-2 text-sm data-[selected=true]:bg-card-soft"
                >
                  <IconoTile
                    categoria={m.categoria}
                    ingreso={m.tipo === "ingreso"}
                    tamano="size-9"
                  />
                  <span className="min-w-0 flex-1 truncate">
                    {m.descripcion || m.categoria || "Sin descripción"}
                  </span>
                  <span className="shrink-0 font-semibold tnum">
                    {m.tipo === "ingreso" ? "+" : "-"}
                    {money(Number(m.monto))}
                  </span>
                </Command.Item>
              ))}
            </Command.Group>
          )}

          <Command.Group
            heading="Acciones"
            className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:text-ink-3"
          >
            <Accion
              icono={ArrowUpRight}
              etiqueta="Registrar gasto"
              onSelect={() => {
                setAbierta(false);
                setBusqueda("");
                abrirCaptura("gasto");
              }}
            />
            <Accion
              icono={ArrowDownLeft}
              etiqueta="Registrar ingreso"
              onSelect={() => {
                setAbierta(false);
                setBusqueda("");
                abrirCaptura("ingreso");
              }}
            />
            <Accion icono={LayoutGrid} etiqueta="Ir al panel" onSelect={() => ir("/")} />
            <Accion
              icono={WalletCards}
              etiqueta="Ver movimientos"
              onSelect={() => ir("/movimientos")}
            />
            <Accion icono={Wallet} etiqueta="Ver cuentas" onSelect={() => ir("/cuentas")} />
            <Accion
              icono={Target}
              etiqueta="Ver presupuestos"
              onSelect={() => ir("/presupuestos")}
            />
            <Accion icono={CreditCard} etiqueta="Ver deudas" onSelect={() => ir("/deudas")} />
            <Accion icono={PiggyBank} etiqueta="Ver ahorros" onSelect={() => ir("/ahorros")} />
            <Accion
              icono={CalendarClock}
              etiqueta="Ver recurrentes"
              onSelect={() => ir("/recurrentes")}
            />
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}

function Accion({
  icono: Icono,
  etiqueta,
  onSelect,
}: {
  icono: typeof Plus;
  etiqueta: string;
  onSelect: () => void;
}) {
  return (
    <Command.Item
      value={etiqueta}
      onSelect={onSelect}
      className="flex h-11 cursor-pointer items-center gap-3 rounded-xl px-3 text-sm font-medium text-ink-2 data-[selected=true]:bg-card-soft data-[selected=true]:text-ink"
    >
      <Icono size={17} />
      {etiqueta}
    </Command.Item>
  );
}
