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
import { Toggle } from "@/components/ui/Toggle";
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
      <HeaderMovil titulo="Deudas y préstamos" subtitulo="Lo que debés y lo que te deben" />
      <div className="hidden lg:block">
        <PageHeader
          titulo="Deudas y préstamos"
          subtitulo="Lo que debés y lo que te deben"
          acciones={
            <Boton onClick={() => setCreando(true)}>
              <Plus size={18} />
              Registrar
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
            <h2 className="px-5 py-4 font-semibold">Lo que debés</h2>
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
            <h2 className="px-5 py-4 font-semibold">Lo que te deben</h2>
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
            {deuda.num_cuotas ? ` · ${deuda.num_cuotas} cuotas` : " · sin cronograma"}
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
  const [cuotas, setCuotas] = useState("3");
  const [inicio, setInicio] = useState(() => new Date().toLocaleDateString("sv-SE"));
  const [cuentaId, setCuentaId] = useState("");
  // Entre personas lo normal es devolver de a poco, sin cronograma fijo
  const [enCuotas, setEnCuotas] = useState(false);
  const [desembolso, setDesembolso] = useState(true);

  const esTarjeta = tipo === "tarjeta";
  const presto = tipo === "prestamo_otorgado";
  const conCuotas = esTarjeta || enCuotas;
  const registraPlata = desembolso && !esTarjeta;

  const valido =
    acreedor.trim() &&
    Number(monto) > 0 &&
    (!conCuotas || Number(cuotas) >= 1) &&
    (!registraPlata || cuentaId);

  function cambiarTipo(t: TipoDeuda) {
    setTipo(t);
    if (t === "tarjeta") setDesembolso(false);
  }

  return (
    <Hoja titulo={esTarjeta ? "Nueva tarjeta" : "Nuevo préstamo"} onCerrar={onCerrar}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!valido) return;
          crear.mutate(
            {
              tipo,
              acreedor: acreedor.trim(),
              monto_total: monto,
              fecha_inicio: inicio,
              generar_cuotas: conCuotas,
              registrar_desembolso: registraPlata,
              ...(conCuotas ? { num_cuotas: Number(cuotas) } : {}),
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
                onClick={() => cambiarTipo(t)}
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
            {presto ? "¿A quién le prestaste?" : esTarjeta ? "Tarjeta" : "¿Quién te prestó?"}
          </span>
          <input
            value={acreedor}
            onChange={(e) => setAcreedor(e.target.value)}
            placeholder={esTarjeta ? "Visa BCP" : "Nombre de la persona"}
            maxLength={120}
            className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent"
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Monto</span>
            <div className="flex items-center gap-2 rounded-xl bg-card-soft px-3.5 focus-within:ring-2 focus-within:ring-accent">
              <span className="text-ink-3">S/</span>
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
            <span className="mb-1.5 block text-sm font-medium">Fecha</span>
            <input
              type="date"
              value={inicio}
              onChange={(e) => setInicio(e.target.value)}
              className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none [color-scheme:inherit] focus:ring-2 focus:ring-accent"
            />
          </label>
        </div>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium">
            {presto ? "Sale de la cuenta" : esTarjeta ? "Pagar desde" : "Entra a la cuenta"}
          </span>
          <select
            value={cuentaId}
            onChange={(e) => setCuentaId(e.target.value)}
            className="h-12 w-full rounded-xl bg-card-soft px-3 text-sm outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="">{registraPlata ? "Elegí una cuenta" : "Elegir después"}</option>
            {(cuentas ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>

        {!esTarjeta && (
          <Interruptor
            activo={desembolso}
            onCambiar={setDesembolso}
            titulo={presto ? "Ya entregaste la plata" : "Ya recibiste la plata"}
            detalle={
              desembolso
                ? `Se registra el movimiento en la cuenta. No cuenta como ${
                    presto ? "gasto" : "ingreso"
                  }: la plata cambia de manos, no de dueño.`
                : "La deuda queda anotada, pero el saldo de tus cuentas no se toca."
            }
          />
        )}

        {!esTarjeta && (
          <Interruptor
            activo={enCuotas}
            onCambiar={setEnCuotas}
            titulo="Devolución en cuotas fijas"
            detalle={
              enCuotas
                ? "Se genera un cronograma con cuotas iguales desde la fecha indicada."
                : "Se salda con los montos que registres, cuando se pueda."
            }
          />
        )}

        {conCuotas && (
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">N.º de cuotas</span>
            <input
              inputMode="numeric"
              value={cuotas}
              onChange={(e) => setCuotas(e.target.value.replace(/\D/g, ""))}
              className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent tnum"
            />
          </label>
        )}

        {crear.isError && (
          <p role="alert" className="text-sm font-medium text-bad-ink">
            No se pudo crear. Si marcaste que la plata ya se movió, elegí una cuenta.
          </p>
        )}

        <div className="flex gap-3 pt-1">
          <Boton type="button" variante="secundario" className="flex-1" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" className="flex-[2]" disabled={!valido || crear.isPending}>
            {crear.isPending ? "Guardando…" : "Guardar"}
          </Boton>
        </div>
      </form>
    </Hoja>
  );
}

function Interruptor({
  activo,
  onCambiar,
  titulo,
  detalle,
}: {
  activo: boolean;
  onCambiar: (v: boolean) => void;
  titulo: string;
  detalle: string;
}) {
  return (
    <div className="rounded-xl bg-card-soft p-3.5">
      <div className="flex items-center gap-3">
        <span className="flex-1 text-sm font-medium">{titulo}</span>
        <Toggle activo={activo} onChange={onCambiar} etiqueta={titulo} />
      </div>
      <p className="mt-1.5 text-xs text-ink-3">{detalle}</p>
    </div>
  );
}
