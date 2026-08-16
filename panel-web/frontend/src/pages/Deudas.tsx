import { ChevronRight, HandCoins, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useCrearDeuda, useCuentas, useDeudas } from "@/api/queries";
import { ETIQUETA_TIPO_DEUDA, type Deuda, type TipoDeuda } from "@/api/types";
import { HeaderMovil } from "@/components/layout/AppShell";
import { BarraProgreso } from "@/components/ui/BarraProgreso";
import { Boton } from "@/components/ui/Boton";
import { Card, PageHeader } from "@/components/ui/Card";
import { Hoja } from "@/components/ui/Hoja";
import { IconoTile } from "@/lib/iconos";
import { money } from "@/lib/money";

export default function Deudas() {
  const { data, isPending } = useDeudas();
  const [creando, setCreando] = useState(false);

  const activas = (data?.items ?? []).filter((d) => d.estado === "activa");
  const debo = activas.filter((d) => d.tipo !== "prestamo_otorgado");
  const meDeben = activas.filter((d) => d.tipo === "prestamo_otorgado");

  const totalDebo = debo.reduce((s, d) => s + d.monto_total, 0);
  const pagadoDebo = debo.reduce((s, d) => s + d.pagado, 0);
  const totalPrestado = meDeben.reduce((s, d) => s + d.monto_total, 0);
  const cobrado = meDeben.reduce((s, d) => s + d.pagado, 0);

  return (
    <>
      <HeaderMovil titulo="Deudas" subtitulo="Lo que debés y lo que te deben" />
      <div className="hidden lg:block">
        <PageHeader
          titulo="Deudas"
          subtitulo="Lo que debés y lo que te deben"
          acciones={
            <Boton onClick={() => setCreando(true)}>
              <Plus size={18} />
              Nueva deuda
            </Boton>
          }
        />
      </div>

      {isPending && <div className="h-32 animate-pulse rounded-2xl bg-card" />}

      {data && (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Totales */}
          <Card>
            <h2 className="font-semibold text-ink-2">Lo que debés</h2>
            <p className="mt-3 text-[2.25rem] font-bold leading-none tracking-tight text-bad-ink tnum">
              {money(data.debo)}
            </p>
            <p className="mt-3 text-sm text-ink-2">
              {debo.length} deuda{debo.length === 1 ? "" : "s"} activa
              {debo.length === 1 ? "" : "s"}
              {proximaCuota(debo) && ` · próxima cuota el ${proximaCuota(debo)}`}
            </p>
            <BarraProgreso
              className="mt-3"
              porcentaje={totalDebo > 0 ? (pagadoDebo / totalDebo) * 100 : 0}
              tono="bad"
            />
            <p className="mt-2 text-sm text-ink-3 tnum">
              Pagaste {money(pagadoDebo)} de {money(totalDebo)}
            </p>
          </Card>

          <Card>
            <h2 className="font-semibold text-ink-2">Lo que te deben</h2>
            <p className="mt-3 text-[2.25rem] font-bold leading-none tracking-tight text-good-ink tnum">
              {money(data.me_deben)}
            </p>
            <p className="mt-3 text-sm text-ink-2">
              {meDeben.length} préstamo{meDeben.length === 1 ? "" : "s"}
              {proximaCuota(meDeben) && ` · próximo cobro el ${proximaCuota(meDeben)}`}
            </p>
            <BarraProgreso
              className="mt-3"
              porcentaje={totalPrestado > 0 ? (cobrado / totalPrestado) * 100 : 0}
              tono="good"
            />
            <p className="mt-2 text-sm text-ink-3 tnum">
              Cobraste {money(cobrado)} de {money(totalPrestado)}
            </p>
          </Card>

          {/* Listas */}
          <Card padding="p-0">
            <h2 className="px-5 py-4 font-semibold">Deudas que tenés</h2>
            {debo.length === 0 ? (
              <Vacio texto="No tenés deudas activas. Cuando registres un préstamo o tarjeta aparecerá acá." />
            ) : (
              <ul className="px-2 pb-2">
                {debo.map((d) => (
                  <FilaDeuda key={d.id} deuda={d} tono="accent" />
                ))}
              </ul>
            )}
          </Card>

          <Card padding="p-0">
            <h2 className="px-5 py-4 font-semibold">Te deben</h2>
            {meDeben.length === 0 ? (
              <Vacio
                icono
                texto="Registrá acá la plata que prestaste para no perderle el rastro"
              />
            ) : (
              <ul className="px-2 pb-2">
                {meDeben.map((d) => (
                  <FilaDeuda key={d.id} deuda={d} tono="good" />
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}

      {creando && <FormDeuda onCerrar={() => setCreando(false)} />}
    </>
  );
}

function proximaCuota(deudas: Deuda[]): string | null {
  const fechas = deudas
    .map((d) => d.proxima_cuota?.vence_en)
    .filter((f): f is string => !!f)
    .sort();
  if (!fechas[0]) return null;
  const [, m, dd] = fechas[0].split("-").map(Number);
  const meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  return `${dd} ${meses[m - 1]}`;
}

function FilaDeuda({ deuda, tono }: { deuda: Deuda; tono: "accent" | "good" }) {
  return (
    <li>
      <Link
        to={`/deudas/${deuda.id}`}
        className="flex items-center gap-3 rounded-xl px-3 py-3.5 transition-colors hover:bg-card-soft"
      >
        <IconoTile categoria={deuda.tipo === "tarjeta" ? "Finanzas" : "Otros"} ingreso={tono === "good"} />
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{deuda.acreedor}</p>
          <p className="mt-0.5 truncate text-sm text-ink-2">
            {ETIQUETA_TIPO_DEUDA[deuda.tipo]}
            {deuda.num_cuotas ? ` · ${deuda.num_cuotas} cuotas` : ""}
          </p>
          <BarraProgreso
            className="mt-2"
            altura="h-1.5"
            porcentaje={deuda.porcentaje_pagado}
            tono={tono}
          />
        </div>
        <div className="shrink-0 text-right">
          <p className={`font-bold tnum ${tono === "good" ? "text-good-ink" : ""}`}>
            {money(deuda.saldo_pendiente)}
          </p>
          {deuda.proxima_cuota && (
            <p className="mt-0.5 text-xs text-ink-3">
              Cuota {deuda.proxima_cuota.numero} de {deuda.num_cuotas ?? "?"}
            </p>
          )}
        </div>
        <ChevronRight size={18} className="shrink-0 text-ink-3" />
      </Link>
    </li>
  );
}

function Vacio({ texto, icono }: { texto: string; icono?: boolean }) {
  return (
    <div className="px-6 pb-10 pt-4 text-center">
      {icono && <HandCoins size={28} className="mx-auto mb-3 text-ink-3" />}
      <p className="text-sm text-ink-3">{texto}</p>
    </div>
  );
}

export function FormDeuda({ onCerrar }: { onCerrar: () => void }) {
  const { data: cuentas } = useCuentas();
  const crear = useCrearDeuda();
  const [tipo, setTipo] = useState<TipoDeuda>("prestamo_recibido");
  const [acreedor, setAcreedor] = useState("");
  const [monto, setMonto] = useState("");
  const [cuotas, setCuotas] = useState("1");
  const [inicio, setInicio] = useState(() => new Date().toLocaleDateString("sv-SE"));
  const [cuentaId, setCuentaId] = useState("");

  const valido = acreedor.trim() && Number(monto) > 0 && Number(cuotas) >= 1;

  return (
    <Hoja titulo="Nueva deuda" onCerrar={onCerrar}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!valido) return;
          crear.mutate(
            {
              tipo,
              acreedor: acreedor.trim(),
              monto_total: monto,
              num_cuotas: Number(cuotas),
              fecha_inicio: inicio,
              ...(cuentaId ? { cuenta_id: Number(cuentaId) } : {}),
            },
            { onSuccess: onCerrar },
          );
        }}
        className="space-y-4"
      >
        <div>
          <span className="mb-1.5 block text-sm font-medium">Tipo</span>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(ETIQUETA_TIPO_DEUDA) as TipoDeuda[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTipo(t)}
                aria-pressed={tipo === t}
                className={`h-11 rounded-full px-4 text-sm font-medium transition-colors ${
                  tipo === t
                    ? "bg-accent-soft text-accent-ink ring-1 ring-accent/40"
                    : "bg-card-soft text-ink-2"
                }`}
              >
                {ETIQUETA_TIPO_DEUDA[t]}
              </button>
            ))}
          </div>
        </div>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium">
            {tipo === "prestamo_otorgado" ? "¿A quién le prestaste?" : "¿A quién le debés?"}
          </span>
          <input
            value={acreedor}
            onChange={(e) => setAcreedor(e.target.value)}
            maxLength={120}
            className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent"
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Monto total</span>
            <div className="flex items-center gap-2 rounded-xl bg-card-soft px-3.5 focus-within:ring-2 focus-within:ring-accent">
              <span className="text-ink-3">$</span>
              <input
                inputMode="decimal"
                value={monto}
                onChange={(e) => setMonto(e.target.value.replace(/[^\d.]/g, ""))}
                placeholder="0.00"
                className="h-12 min-w-0 flex-1 bg-transparent text-sm outline-none tnum"
              />
            </div>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">N.º de cuotas</span>
            <input
              inputMode="numeric"
              value={cuotas}
              onChange={(e) => setCuotas(e.target.value.replace(/\D/g, ""))}
              className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent tnum"
            />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Primera cuota</span>
            <input
              type="date"
              value={inicio}
              onChange={(e) => setInicio(e.target.value)}
              className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none [color-scheme:inherit] focus:ring-2 focus:ring-accent"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Pagar desde</span>
            <select
              value={cuentaId}
              onChange={(e) => setCuentaId(e.target.value)}
              className="h-12 w-full rounded-xl bg-card-soft px-3 text-sm outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="">Elegir al pagar</option>
              {(cuentas ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
        </div>

        <p className="text-sm text-ink-3">
          Se generará el cronograma con cuotas iguales desde la fecha indicada.
        </p>

        {crear.isError && (
          <p role="alert" className="text-sm font-medium text-bad-ink">
            No se pudo crear la deuda.
          </p>
        )}

        <div className="flex gap-3 pt-1">
          <Boton type="button" variante="secundario" className="flex-1" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" className="flex-[2]" disabled={!valido || crear.isPending}>
            {crear.isPending ? "Creando…" : "Crear deuda"}
          </Boton>
        </div>
      </form>
    </Hoja>
  );
}
