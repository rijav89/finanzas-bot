import {
  Archive,
  ArrowLeftRight,
  Banknote,
  Landmark,
  Lock,
  Pencil,
  PiggyBank,
  Plus,
} from "lucide-react";
import { useState } from "react";

import {
  useArchivarCuenta,
  useCrearCuenta,
  useCuentas,
  useDashboard,
  useEditarCuenta,
} from "@/api/queries";
import type { Cuenta } from "@/api/types";
import { HeaderMovil } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { Boton } from "@/components/ui/Boton";
import { Card, PageHeader } from "@/components/ui/Card";
import { Hoja } from "@/components/ui/Hoja";
import { money } from "@/lib/money";

export default function Cuentas() {
  const { data: cuentas, isPending } = useCuentas();
  const { data: dash } = useDashboard();
  const archivar = useArchivarCuenta();
  const editar = useEditarCuenta();
  const [creando, setCreando] = useState(false);

  const activas = cuentas ?? [];
  const saldoDe = (id: number) =>
    Number(dash?.saldos_por_cuenta.find((s) => s.cuenta_id === id)?.saldo ?? 0);
  const consolidado = activas.reduce((s, c) => s + saldoDe(c.id), 0);

  return (
    <>
      <HeaderMovil titulo="Cuentas" subtitulo={`${activas.length} activas`} />
      <div className="hidden lg:block">
        <PageHeader
          titulo="Cuentas"
          subtitulo={`${activas.length} activas · saldo consolidado ${money(consolidado)}`}
          acciones={
            <Boton onClick={() => setCreando(true)}>
              <Plus size={18} />
              Nueva cuenta
            </Boton>
          }
        />
      </div>

      {isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-44 animate-pulse rounded-2xl bg-card" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {activas.map((c) => (
            <TarjetaCuenta
              key={c.id}
              cuenta={c}
              saldo={saldoDe(c.id)}
              onArchivar={() => archivar.mutate(c.id)}
              onTipo={() =>
                editar.mutate({
                  id: c.id,
                  tipo: c.tipo === "ahorro" ? "corriente" : "ahorro",
                })
              }
              onRenombrar={() => {
                const nombre = window.prompt("Nuevo nombre de la cuenta", c.nombre);
                if (nombre?.trim()) editar.mutate({ id: c.id, nombre: nombre.trim() });
              }}
            />
          ))}

          <button
            onClick={() => setCreando(true)}
            className="flex min-h-44 flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-hairline bg-card-soft/60 p-6 text-center transition-colors hover:border-accent/50"
          >
            <span className="flex size-11 items-center justify-center rounded-full bg-card text-accent shadow-sm ring-1 ring-[var(--ring)]">
              <Plus size={20} />
            </span>
            <span className="font-semibold">Agregar cuenta</span>
            <span className="text-sm text-ink-3">Definí nombre, tipo y saldo inicial</span>
          </button>
        </div>
      )}

      {creando && <FormCuenta onCerrar={() => setCreando(false)} />}
    </>
  );
}

function TarjetaCuenta({
  cuenta,
  saldo,
  onArchivar,
  onTipo,
  onRenombrar,
}: {
  cuenta: Cuenta;
  saldo: number;
  onArchivar: () => void;
  onTipo: () => void;
  onRenombrar: () => void;
}) {
  const esAhorro = cuenta.tipo === "ahorro";
  const Icono = esAhorro ? PiggyBank : cuenta.es_principal ? Landmark : Banknote;

  return (
    <Card className="flex flex-col">
      <div className="flex items-center gap-2.5">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-card-soft text-ink-2">
          <Icono size={18} />
        </span>
        <h2 className="min-w-0 flex-1 truncate font-semibold">{cuenta.nombre}</h2>
        {cuenta.es_principal ? (
          <Badge tono="accent">Principal</Badge>
        ) : esAhorro ? (
          <Badge tono="good">Ahorro</Badge>
        ) : null}
      </div>

      <p className="mt-4 text-[2rem] font-bold leading-none tracking-tight tnum">
        {money(saldo)}
      </p>
      <p className="mt-2 text-sm text-ink-2">
        {esAhorro ? "Ahorro" : "Corriente"} · saldo inicial{" "}
        {money(Number(cuenta.saldo_inicial ?? 0))}
      </p>

      <div className="mt-4 flex items-center gap-4 border-t border-hairline pt-3 text-sm">
        <button
          onClick={onRenombrar}
          className="inline-flex items-center gap-1.5 font-medium text-ink-2 hover:text-ink"
        >
          <Pencil size={15} />
          Renombrar
        </button>
        <button
          onClick={onTipo}
          className="inline-flex items-center gap-1.5 font-medium text-ink-2 hover:text-ink"
        >
          <ArrowLeftRight size={15} />
          Tipo
        </button>
        {cuenta.es_principal ? (
          <span className="ml-auto inline-flex items-center gap-1.5 text-ink-3">
            <Lock size={15} />
            Protegida
          </span>
        ) : (
          <button
            onClick={onArchivar}
            className="ml-auto inline-flex items-center gap-1.5 font-medium text-ink-2 hover:text-ink"
          >
            <Archive size={15} />
            Archivar
          </button>
        )}
      </div>
    </Card>
  );
}

function FormCuenta({ onCerrar }: { onCerrar: () => void }) {
  const crear = useCrearCuenta();
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState<"corriente" | "ahorro">("corriente");
  const [saldo, setSaldo] = useState("");

  return (
    <Hoja titulo="Nueva cuenta" onCerrar={onCerrar}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!nombre.trim()) return;
          crear.mutate(
            { nombre: nombre.trim(), tipo, saldo_inicial: saldo || "0" },
            { onSuccess: onCerrar },
          );
        }}
        className="space-y-4"
      >
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium">Nombre</span>
          <input
            autoFocus
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Cuenta corriente, Efectivo…"
            maxLength={80}
            className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent"
          />
        </label>

        <div>
          <span className="mb-1.5 block text-sm font-medium">Tipo</span>
          <div className="flex gap-2">
            {(["corriente", "ahorro"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTipo(t)}
                aria-pressed={tipo === t}
                className={`h-11 flex-1 rounded-xl text-sm font-semibold capitalize transition-colors ${
                  tipo === t
                    ? "bg-accent-soft text-accent-ink ring-1 ring-accent/40"
                    : "bg-card-soft text-ink-2"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium">Saldo inicial</span>
          <div className="flex items-center gap-2 rounded-xl bg-card-soft px-3.5 focus-within:ring-2 focus-within:ring-accent">
            <span className="text-ink-3">$</span>
            <input
              inputMode="decimal"
              value={saldo}
              onChange={(e) => setSaldo(e.target.value.replace(/[^\d.]/g, ""))}
              placeholder="0.00"
              className="h-12 min-w-0 flex-1 bg-transparent text-sm outline-none tnum"
            />
          </div>
        </label>

        {crear.isError && (
          <p role="alert" className="text-sm font-medium text-bad-ink">
            No se pudo crear la cuenta (¿nombre repetido?).
          </p>
        )}

        <div className="flex gap-3 pt-1">
          <Boton type="button" variante="secundario" className="flex-1" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" className="flex-[2]" disabled={!nombre.trim() || crear.isPending}>
            {crear.isPending ? "Creando…" : "Crear cuenta"}
          </Boton>
        </div>
      </form>
    </Hoja>
  );
}
