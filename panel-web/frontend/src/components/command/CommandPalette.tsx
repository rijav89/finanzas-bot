import { Command } from "cmdk";
import { LayoutDashboard, ListOrdered, Plus, Wallet } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useMovimientos } from "@/api/queries";
import { money } from "@/lib/money";
import { useUiStore } from "@/stores/uiStore";

export function CommandPalette() {
  const abierta = useUiStore((s) => s.paletaAbierta);
  const setAbierta = useUiStore((s) => s.setPaletaAbierta);
  const setGastoRapido = useUiStore((s) => s.setGastoRapidoAbierto);
  const [busqueda, setBusqueda] = useState("");
  const navigate = useNavigate();

  // Ctrl/Cmd+K en desktop; en móvil el disparador es el botón de búsqueda del shell
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
      className="fixed inset-0 z-50 bg-black/40 p-4 pt-[10vh]"
      onClick={() => setAbierta(false)}
    >
      <Command
        label="Paleta de comandos"
        className="mx-auto max-w-lg overflow-hidden rounded-2xl bg-card shadow-2xl ring-1 ring-[var(--border-ring)]"
        onClick={(e) => e.stopPropagation()}
        shouldFilter={false}
      >
        <Command.Input
          autoFocus
          value={busqueda}
          onValueChange={setBusqueda}
          placeholder="Buscar movimientos o ir a…"
          className="w-full border-b border-hairline bg-transparent px-4 py-3.5 text-ink outline-none placeholder:text-ink-3"
        />
        <Command.List className="max-h-80 overflow-y-auto p-2">
          <Command.Empty className="px-3 py-6 text-center text-sm text-ink-3">
            Sin resultados.
          </Command.Empty>

          {resultados.length > 0 && (
            <Command.Group
              heading="Movimientos"
              className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-ink-3"
            >
              {resultados.map((m) => (
                <Command.Item
                  key={`${m.tipo}-${m.id}`}
                  value={`mov-${m.tipo}-${m.id}`}
                  onSelect={() => ir("/movimientos")}
                  className="flex touch-44 cursor-pointer items-center gap-3 rounded-xl px-3 text-sm data-[selected=true]:bg-page"
                >
                  <span className="truncate text-ink-2">
                    {m.descripcion || m.categoria || "(sin descripción)"}
                  </span>
                  <span className="ml-auto shrink-0 font-medium tabular-nums">
                    {money(Number(m.monto))}
                  </span>
                </Command.Item>
              ))}
            </Command.Group>
          )}

          <Command.Group
            heading="Acciones"
            className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-ink-3"
          >
            <Accion
              icono={Plus}
              etiqueta="Registrar gasto"
              onSelect={() => {
                setAbierta(false);
                setBusqueda("");
                setGastoRapido(true);
              }}
            />
            <Accion icono={LayoutDashboard} etiqueta="Ir al panel" onSelect={() => ir("/")} />
            <Accion
              icono={ListOrdered}
              etiqueta="Ver movimientos"
              onSelect={() => ir("/movimientos")}
            />
            <Accion icono={Wallet} etiqueta="Ver cuentas" onSelect={() => ir("/cuentas")} />
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
      className="flex touch-44 cursor-pointer items-center gap-3 rounded-xl px-3 text-sm text-ink-2 data-[selected=true]:bg-page data-[selected=true]:text-ink"
    >
      <Icono size={16} />
      {etiqueta}
    </Command.Item>
  );
}
