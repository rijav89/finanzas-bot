import { ChevronRight, Plus, X } from "lucide-react";
import { useState } from "react";

import {
  useCrearDeuda,
  useCuentas,
  useDeuda,
  useDeudas,
  usePagarCuota,
} from "@/api/queries";
import { ETIQUETA_TIPO_DEUDA, type TipoDeuda } from "@/api/types";
import { BarraProgreso } from "@/components/ui/BarraProgreso";
import { Boton } from "@/components/ui/Boton";
import { cn } from "@/lib/cn";
import { money } from "@/lib/money";

export default function Deudas() {
  const { data, isLoading } = useDeudas();
  const [detalleId, setDetalleId] = useState<number | null>(null);
  const [creando, setCreando] = useState(false);

  return (
    <div className="mx-auto max-w-3xl pb-8">
      <header className="flex items-center gap-3 py-4">
        <h1 className="text-xl font-semibold">Deudas</h1>
        <Boton className="ml-auto" onClick={() => setCreando(true)}>
          <Plus size={16} className="mr-1.5 inline" />
          Nueva
        </Boton>
      </header>

      {isLoading && <div className="h-32 animate-pulse rounded-2xl bg-card" />}

      {data && (
        <>
          <section className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-card p-4 ring-1 ring-[var(--border-ring)]">
              <p className="text-xs text-ink-2">Debo</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-critical">
                {money(data.debo)}
              </p>
            </div>
            <div className="rounded-2xl bg-card p-4 ring-1 ring-[var(--border-ring)]">
              <p className="text-xs text-ink-2">Me deben</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-good-text">
                {money(data.me_deben)}
              </p>
            </div>
          </section>

          {data.items.length === 0 ? (
            <p className="mt-4 rounded-2xl bg-card p-6 text-center text-sm text-ink-3 ring-1 ring-[var(--border-ring)]">
              Sin deudas registradas. Podés anotar préstamos, tarjetas o plata que te deben.
            </p>
          ) : (
            <section className="mt-4 space-y-2">
              {data.items.map((d) => (
                <button
                  key={d.id}
                  onClick={() => setDetalleId(d.id)}
                  className="flex w-full items-center gap-3 rounded-xl bg-card p-3.5 text-left ring-1 ring-[var(--border-ring)] hover:ring-accent/40"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="truncate font-medium">{d.acreedor}</span>
                      {d.estado === "pagada" && (
                        <span className="shrink-0 rounded-full bg-good/15 px-2 py-0.5 text-[11px] font-medium text-good-text">
                          Pagada
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-ink-3">
                      {ETIQUETA_TIPO_DEUDA[d.tipo]}
                      {d.cuotas_pendientes > 0 && ` · ${d.cuotas_pendientes} cuotas pendientes`}
                    </p>
                    <BarraProgreso
                      className="mt-2"
                      porcentaje={d.porcentaje_pagado}
                      estado={d.estado === "pagada" ? "bien" : "info"}
                    />
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-sm font-semibold tabular-nums">
                      {money(d.saldo_pendiente)}
                    </p>
                    <p className="text-xs text-ink-3">de {money(d.monto_total)}</p>
                  </div>
                  <ChevronRight size={18} className="shrink-0 text-ink-3" />
                </button>
              ))}
            </section>
          )}
        </>
      )}

      {detalleId !== null && (
        <DetalleDeuda id={detalleId} onCerrar={() => setDetalleId(null)} />
      )}
      {creando && <FormDeuda onCerrar={() => setCreando(false)} />}
    </div>
  );
}

function DetalleDeuda({ id, onCerrar }: { id: number; onCerrar: () => void }) {
  const { data, isLoading } = useDeuda(id);
  const pagar = usePagarCuota();

  return (
    <Hoja titulo={data?.acreedor ?? "Deuda"} onCerrar={onCerrar}>
      {isLoading && <div className="h-40 animate-pulse rounded-xl bg-page" />}
      {data && (
        <>
          <p className="text-sm text-ink-2">{ETIQUETA_TIPO_DEUDA[data.tipo]}</p>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-sm text-ink-2">Pagado</span>
            <span className="tabular-nums">
              {money(data.pagado)} <span className="text-ink-3">/ {money(data.monto_total)}</span>
            </span>
          </div>
          <BarraProgreso className="mt-2" porcentaje={data.porcentaje_pagado} estado="info" />

          {data.tasa_interes != null && (
            <p className="mt-3 text-xs text-ink-3">Tasa: {data.tasa_interes}% TEA</p>
          )}

          <h3 className="mt-5 text-sm font-medium text-ink-2">Cuotas</h3>
          <ul className="mt-2 space-y-1.5">
            {data.cuotas.map((c) => (
              <li
                key={c.numero}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm ring-1",
                  c.pagada
                    ? "bg-page text-ink-3 ring-transparent"
                    : "bg-page ring-[var(--border-ring)]",
                )}
              >
                <span className="w-7 shrink-0 text-xs text-ink-3">#{c.numero}</span>
                <span className={cn("tabular-nums", c.pagada && "line-through")}>
                  {money(c.monto)}
                </span>
                <span className="text-xs text-ink-3">{c.vence_en}</span>
                <span className="ml-auto">
                  {c.pagada ? (
                    <span className="text-xs text-good-text">Pagada</span>
                  ) : (
                    <Boton
                      variante="secundario"
                      disabled={pagar.isPending}
                      onClick={() => pagar.mutate({ deudaId: id, numero: c.numero })}
                    >
                      Pagar
                    </Boton>
                  )}
                </span>
              </li>
            ))}
          </ul>
          {data.cuotas.length === 0 && (
            <p className="mt-2 text-sm text-ink-3">Esta deuda no tiene cuotas programadas.</p>
          )}
          {pagar.isError && (
            <p role="alert" className="mt-3 text-sm text-critical">
              No se pudo registrar el pago.
            </p>
          )}
          <p className="mt-4 text-xs text-ink-3">
            Al pagar una cuota se registra el gasto automáticamente en tu historial.
          </p>
        </>
      )}
    </Hoja>
  );
}

function FormDeuda({ onCerrar }: { onCerrar: () => void }) {
  const { data: cuentas } = useCuentas();
  const crear = useCrearDeuda();
  const [tipo, setTipo] = useState<TipoDeuda>("prestamo_recibido");
  const [acreedor, setAcreedor] = useState("");
  const [monto, setMonto] = useState("");
  const [cuotas, setCuotas] = useState("1");
  const [inicio, setInicio] = useState(() => new Date().toLocaleDateString("sv-SE"));
  const [cuentaId, setCuentaId] = useState<string>("");

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
        className="space-y-3"
      >
        <Campo etiqueta="Tipo">
          <select
            value={tipo}
            onChange={(e) => setTipo(e.target.value as TipoDeuda)}
            className="h-11 w-full rounded-xl bg-page px-3 text-sm ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
          >
            {Object.entries(ETIQUETA_TIPO_DEUDA).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </Campo>

        <Campo etiqueta={tipo === "prestamo_otorgado" ? "¿A quién le prestaste?" : "¿A quién le debés?"}>
          <input
            autoFocus
            value={acreedor}
            onChange={(e) => setAcreedor(e.target.value)}
            maxLength={120}
            className="h-11 w-full rounded-xl bg-page px-3 text-sm ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
          />
        </Campo>

        <div className="grid grid-cols-2 gap-3">
          <Campo etiqueta="Monto total">
            <input
              inputMode="decimal"
              value={monto}
              onChange={(e) => setMonto(e.target.value.replace(/[^\d.]/g, ""))}
              placeholder="0.00"
              className="h-11 w-full rounded-xl bg-page px-3 text-sm tabular-nums ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
            />
          </Campo>
          <Campo etiqueta="N.º de cuotas">
            <input
              inputMode="numeric"
              value={cuotas}
              onChange={(e) => setCuotas(e.target.value.replace(/\D/g, ""))}
              className="h-11 w-full rounded-xl bg-page px-3 text-sm tabular-nums ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
            />
          </Campo>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Campo etiqueta="Primera cuota">
            <input
              type="date"
              value={inicio}
              onChange={(e) => setInicio(e.target.value)}
              className="h-11 w-full rounded-xl bg-page px-3 text-sm ring-1 ring-[var(--border-ring)] outline-none [color-scheme:inherit] focus:ring-2 focus:ring-accent"
            />
          </Campo>
          <Campo etiqueta="Pagar desde">
            <select
              value={cuentaId}
              onChange={(e) => setCuentaId(e.target.value)}
              className="h-11 w-full rounded-xl bg-page px-3 text-sm ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="">Elegir al pagar</option>
              {(cuentas ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </Campo>
        </div>

        <p className="text-xs text-ink-3">
          Se generará el cronograma con cuotas iguales desde la fecha indicada.
        </p>

        {crear.isError && (
          <p role="alert" className="text-sm text-critical">
            No se pudo crear la deuda.
          </p>
        )}

        <div className="flex gap-3 pt-2">
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

function Campo({ etiqueta, children }: { etiqueta: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-ink-2">{etiqueta}</span>
      {children}
    </label>
  );
}

/** Hoja modal reutilizable: bottom sheet en móvil, diálogo centrado en desktop. */
function Hoja({
  titulo,
  onCerrar,
  children,
}: {
  titulo: string;
  onCerrar: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4"
      onClick={onCerrar}
    >
      <div
        role="dialog"
        aria-label={titulo}
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[92dvh] w-full max-w-lg flex-col rounded-t-2xl bg-card shadow-2xl ring-1 ring-[var(--border-ring)] sm:max-h-[85dvh] sm:rounded-2xl"
      >
        <header className="flex shrink-0 items-center gap-3 border-b border-hairline px-4 py-3 sm:px-5">
          <h2 className="truncate font-semibold">{titulo}</h2>
          <button
            onClick={onCerrar}
            aria-label="Cerrar"
            className="ml-auto flex size-9 items-center justify-center rounded-lg text-ink-3 hover:text-ink"
          >
            <X size={18} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] sm:p-5">
          {children}
        </div>
      </div>
    </div>
  );
}
