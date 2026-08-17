import { ArrowLeft, Check, Info, Pencil, Plus } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  useCuentas,
  useDeuda,
  usePagarCuota,
  useRegistrarMovimientoDeuda,
} from "@/api/queries";
import { ETIQUETA_TIPO_DEUDA, type Deuda } from "@/api/types";
import { Badge } from "@/components/ui/Badge";
import { BarraProgreso } from "@/components/ui/BarraProgreso";
import { Boton } from "@/components/ui/Boton";
import { Card, PageHeader } from "@/components/ui/Card";
import { Hoja } from "@/components/ui/Hoja";
import { cn } from "@/lib/cn";
import { money } from "@/lib/money";

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

export default function DeudaDetalle() {
  const { id } = useParams();
  const deudaId = Number(id);
  const { data, isPending, isError } = useDeuda(Number.isFinite(deudaId) ? deudaId : null);
  const pagar = usePagarCuota();
  const [registrando, setRegistrando] = useState(false);

  if (isPending) return <div className="h-40 animate-pulse rounded-2xl bg-card" />;
  if (isError || !data) return <p className="text-sm text-bad-ink">No se encontró la deuda.</p>;

  const proxima = data.cuotas.find((c) => !c.pagada);
  const pagadas = data.cuotas.filter((c) => c.pagada).length;
  const alDia = !proxima || diasHasta(proxima.vence_en) >= 0;
  // Cuando te devuelven un préstamo la plata entra: no es «pagar», es «cobrar»
  const meDeben = data.tipo === "prestamo_otorgado";
  const abierta = data.estado === "activa";

  return (
    <>
      <PageHeader
        titulo={data.acreedor}
        subtitulo={
          <>
            {ETIQUETA_TIPO_DEUDA[data.tipo]}
            {data.num_cuotas && data.cuotas[0]
              ? ` · ${data.num_cuotas} cuotas de ${money(data.cuotas[0].monto)}`
              : " · se salda con montos sueltos"}
          </>
        }
        acciones={
          <>
            <Boton variante="secundario">
              <Pencil size={16} />
              Editar
            </Boton>
            {data.sin_cronograma
              ? abierta && (
                  <Boton onClick={() => setRegistrando(true)}>
                    <Plus size={17} />
                    {meDeben ? "Registrar cobro" : "Registrar pago"}
                  </Boton>
                )
              : proxima && (
                  <Boton
                    disabled={pagar.isPending}
                    onClick={() => pagar.mutate({ deudaId, numero: proxima.numero })}
                  >
                    <Check size={17} />
                    {meDeben ? "Registrar cobro" : "Registrar pago"}
                  </Boton>
                )}
          </>
        }
      />

      <Link
        to="/deudas"
        className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-ink-2 hover:text-ink"
      >
        <ArrowLeft size={16} />
        Volver a deudas
      </Link>

      {/* Resumen */}
      <Card className="mb-4">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-semibold text-ink-2">
            {meDeben ? "Resumen del préstamo" : "Resumen de la deuda"}
          </h2>
          <p className="ml-auto text-sm text-ink-3">
            {data.sin_cronograma
              ? "Se cierra sola al completar el monto"
              : "Se cierra sola al pagar la última cuota"}
          </p>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-x-10 gap-y-4">
          <Metrica etiqueta="Monto total" valor={money(data.monto_total)} />
          <Metrica etiqueta="Pagado" valor={money(data.pagado)} clase="text-good-ink" />
          <Metrica
            etiqueta="Restante"
            valor={money(data.saldo_pendiente)}
            clase="text-bad-ink"
          />
          {!data.sin_cronograma && data.cuotas[0] && (
            <Metrica etiqueta="Cuota" valor={money(data.cuotas[0].monto)} />
          )}
          <div className="min-w-[14rem] flex-1">
            <div className="mb-2 flex items-center justify-end gap-2">
              <span className="text-sm text-ink-2 tnum">
                {data.sin_cronograma
                  ? `${pagadas} movimiento${pagadas === 1 ? "" : "s"} registrado${pagadas === 1 ? "" : "s"}`
                  : `${pagadas} de ${data.cuotas.length} cuotas pagadas`}
              </span>
              <Badge tono={data.estado === "pagada" ? "good" : alDia ? "good" : "warn"}>
                {data.estado === "pagada" ? "Pagada" : alDia ? "Al día" : "Vencida"}
              </Badge>
            </div>
            <BarraProgreso porcentaje={data.porcentaje_pagado} tono="accent" />
          </div>
        </div>
      </Card>

      {/* Cronograma */}
      <Card padding="p-0">
        <div className="flex flex-wrap items-center gap-2 px-5 py-4">
          <h2 className="font-semibold">
            {data.sin_cronograma ? "Movimientos" : "Cronograma de cuotas"}
          </h2>
          <p className="ml-auto inline-flex items-center gap-1.5 text-sm text-ink-3">
            {data.tipo === "tarjeta"
              ? "Cada pago se registra como gasto en tu historial"
              : "Mueven tu saldo, pero no cuentan como ingreso ni gasto del mes"}
            <Info size={14} />
          </p>
        </div>

        {data.cuotas.length === 0 ? (
          <p className="px-5 pb-8 text-sm text-ink-3">
            {data.sin_cronograma
              ? `Todavía no registraste ningún ${meDeben ? "cobro" : "pago"}.`
              : "Esta deuda no tiene cuotas programadas."}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[46rem] text-sm">
              <thead>
                <tr className="border-y border-hairline text-left text-ink-2">
                  <th className="px-5 py-2.5 font-medium">{data.sin_cronograma ? "#" : "Cuota"}</th>
                  <th className="px-5 py-2.5 font-medium">
                    {data.sin_cronograma ? "Fecha" : "Vencimiento"}
                  </th>
                  <th className="px-5 py-2.5 font-medium">Monto</th>
                  <th className="px-5 py-2.5 font-medium">Estado</th>
                  <th className="px-5 py-2.5 font-medium">Registrada como</th>
                  <th className="px-5 py-2.5" />
                </tr>
              </thead>
              <tbody>
                {data.cuotas.map((c) => {
                  const esProxima = proxima?.numero === c.numero;
                  const dias = diasHasta(c.vence_en);
                  return (
                    <tr
                      key={c.numero}
                      className={cn(
                        "border-b border-hairline last:border-0",
                        esProxima && "bg-warn-soft",
                      )}
                    >
                      <td className="px-5 py-3.5 font-semibold tnum">
                        {String(c.numero).padStart(2, "0")} / {data.cuotas.length}
                      </td>
                      <td className="px-5 py-3.5 tnum">{fechaLarga(c.vence_en)}</td>
                      <td className="px-5 py-3.5 font-semibold tnum">{money(c.monto)}</td>
                      <td className="px-5 py-3.5">
                        {c.pagada ? (
                          <Badge tono="good">Pagada</Badge>
                        ) : esProxima ? (
                          <span className="inline-flex items-center gap-1.5 font-medium text-warn-ink">
                            <span aria-hidden className="size-1.5 rounded-full bg-warn" />
                            {dias < 0
                              ? `Venció hace ${-dias} días`
                              : dias === 0
                                ? "Vence hoy"
                                : `Vence en ${dias} días`}
                          </span>
                        ) : (
                          <span className="text-ink-2">Pendiente</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-ink-2">
                        {c.pagada
                          ? `${c.ingreso_id ? "Ingreso" : "Gasto"} · ${categoriaDe(data)}`
                          : esProxima
                            ? "Se registrará al pagar"
                            : "—"}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        {!c.pagada && esProxima && (
                          <button
                            onClick={() => pagar.mutate({ deudaId, numero: c.numero })}
                            disabled={pagar.isPending}
                            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-accent px-3 text-sm font-semibold text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
                          >
                            <Check size={15} />
                            {meDeben ? "Cobrar" : "Pagar"}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {pagar.isError && (
          <p role="alert" className="px-5 py-3 text-sm font-medium text-bad-ink">
            No se pudo registrar el pago.
          </p>
        )}
      </Card>

      {registrando && (
        <FormMovimiento
          deuda={data}
          onCerrar={() => setRegistrando(false)}
        />
      )}
    </>
  );
}

/** La categoría con la que queda el movimiento en el historial. */
function categoriaDe(deuda: Deuda): string {
  return deuda.tipo === "tarjeta" ? "Finanzas" : "Prestamo";
}

function FormMovimiento({ deuda, onCerrar }: { deuda: Deuda; onCerrar: () => void }) {
  const { data: cuentas } = useCuentas();
  const registrar = useRegistrarMovimientoDeuda();
  const meDeben = deuda.tipo === "prestamo_otorgado";

  const [monto, setMonto] = useState(String(deuda.saldo_pendiente));
  const [fecha, setFecha] = useState(() => new Date().toLocaleDateString("sv-SE"));
  const [cuentaId, setCuentaId] = useState(deuda.cuenta_id ? String(deuda.cuenta_id) : "");

  const valor = Number(monto);
  const valido = valor > 0 && valor <= deuda.saldo_pendiente && (cuentaId || deuda.cuenta_id);

  return (
    <Hoja
      titulo={meDeben ? `${deuda.acreedor} te devolvió` : `Devolución a ${deuda.acreedor}`}
      onCerrar={onCerrar}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!valido) return;
          registrar.mutate(
            {
              deudaId: deuda.id,
              monto,
              fecha,
              ...(cuentaId ? { cuenta_id: Number(cuentaId) } : {}),
            },
            { onSuccess: onCerrar },
          );
        }}
        className="space-y-4"
      >
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium">Monto</span>
          <div className="flex items-center gap-2 rounded-xl bg-card-soft px-3.5 focus-within:ring-2 focus-within:ring-accent">
            <span className="text-ink-3">S/</span>
            <input
              autoFocus
              inputMode="decimal"
              value={monto}
              onChange={(e) => setMonto(e.target.value.replace(/[^\d.]/g, ""))}
              className="h-14 min-w-0 flex-1 bg-transparent text-2xl font-bold outline-none tnum"
            />
          </div>
          <span className="mt-1.5 block text-xs text-ink-3 tnum">
            Pendiente: {money(deuda.saldo_pendiente)}
          </span>
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Fecha</span>
            <input
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none [color-scheme:inherit] focus:ring-2 focus:ring-accent"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">
              {meDeben ? "Entra a" : "Sale de"}
            </span>
            <select
              value={cuentaId}
              onChange={(e) => setCuentaId(e.target.value)}
              className="h-12 w-full rounded-xl bg-card-soft px-3 text-sm outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="">Elegí una cuenta</option>
              {(cuentas ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
        </div>

        <p className="text-sm text-ink-3">
          Mueve el saldo de la cuenta, pero no cuenta como{" "}
          {meDeben ? "ingreso" : "gasto"} del mes: es plata que vuelve a su dueño.
        </p>

        {registrar.isError && (
          <p role="alert" className="text-sm font-medium text-bad-ink">
            No se pudo registrar. Revisá que el monto no supere lo pendiente.
          </p>
        )}

        <div className="flex gap-3 pt-1">
          <Boton type="button" variante="secundario" className="flex-1" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" className="flex-[2]" disabled={!valido || registrar.isPending}>
            {registrar.isPending ? "Guardando…" : "Registrar"}
          </Boton>
        </div>
      </form>
    </Hoja>
  );
}

function Metrica({
  etiqueta,
  valor,
  clase,
}: {
  etiqueta: string;
  valor: string;
  clase?: string;
}) {
  return (
    <div>
      <p className="text-sm text-ink-2">{etiqueta}</p>
      <p className={`mt-1 text-[1.75rem] font-bold leading-none tracking-tight tnum ${clase ?? ""}`}>
        {valor}
      </p>
    </div>
  );
}

function diasHasta(iso: string): number {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const [a, m, d] = iso.split("-").map(Number);
  return Math.round((new Date(a, m - 1, d).getTime() - hoy.getTime()) / 86_400_000);
}

function fechaLarga(iso: string): string {
  const [a, m, d] = iso.split("-").map(Number);
  return `${d} de ${MESES[m - 1]} ${a}`;
}
