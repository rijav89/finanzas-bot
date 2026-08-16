import { ArrowLeft, Check, Info, Pencil } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { useDeuda, usePagarCuota } from "@/api/queries";
import { ETIQUETA_TIPO_DEUDA } from "@/api/types";
import { Badge } from "@/components/ui/Badge";
import { BarraProgreso } from "@/components/ui/BarraProgreso";
import { Boton } from "@/components/ui/Boton";
import { Card, PageHeader } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { money } from "@/lib/money";

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

export default function DeudaDetalle() {
  const { id } = useParams();
  const deudaId = Number(id);
  const { data, isPending, isError } = useDeuda(Number.isFinite(deudaId) ? deudaId : null);
  const pagar = usePagarCuota();

  if (isPending) return <div className="h-40 animate-pulse rounded-2xl bg-card" />;
  if (isError || !data) return <p className="text-sm text-bad-ink">No se encontró la deuda.</p>;

  const proxima = data.cuotas.find((c) => !c.pagada);
  const pagadas = data.cuotas.filter((c) => c.pagada).length;
  const alDia = !proxima || diasHasta(proxima.vence_en) >= 0;

  return (
    <>
      <PageHeader
        titulo={data.acreedor}
        subtitulo={
          <>
            {ETIQUETA_TIPO_DEUDA[data.tipo]}
            {data.num_cuotas && data.cuotas[0]
              ? ` · ${data.num_cuotas} cuotas de ${money(data.cuotas[0].monto)}`
              : ""}
          </>
        }
        acciones={
          <>
            <Boton variante="secundario">
              <Pencil size={16} />
              Editar
            </Boton>
            {proxima && (
              <Boton
                disabled={pagar.isPending}
                onClick={() => pagar.mutate({ deudaId, numero: proxima.numero })}
              >
                <Check size={17} />
                Registrar pago
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
          <h2 className="font-semibold text-ink-2">Resumen de la deuda</h2>
          <p className="ml-auto text-sm text-ink-3">Se cierra sola al pagar la última cuota</p>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-x-10 gap-y-4">
          <Metrica etiqueta="Monto total" valor={money(data.monto_total)} />
          <Metrica etiqueta="Pagado" valor={money(data.pagado)} clase="text-good-ink" />
          <Metrica
            etiqueta="Restante"
            valor={money(data.saldo_pendiente)}
            clase="text-bad-ink"
          />
          {data.cuotas[0] && (
            <Metrica etiqueta="Cuota" valor={money(data.cuotas[0].monto)} />
          )}
          <div className="min-w-[14rem] flex-1">
            <div className="mb-2 flex items-center justify-end gap-2">
              <span className="text-sm text-ink-2 tnum">
                {pagadas} de {data.cuotas.length} cuotas pagadas
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
          <h2 className="font-semibold">Cronograma de cuotas</h2>
          <p className="ml-auto inline-flex items-center gap-1.5 text-sm text-ink-3">
            Cada pago se registra como gasto en tu historial
            <Info size={14} />
          </p>
        </div>

        {data.cuotas.length === 0 ? (
          <p className="px-5 pb-8 text-sm text-ink-3">Esta deuda no tiene cuotas programadas.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[46rem] text-sm">
              <thead>
                <tr className="border-y border-hairline text-left text-ink-2">
                  <th className="px-5 py-2.5 font-medium">Cuota</th>
                  <th className="px-5 py-2.5 font-medium">Vencimiento</th>
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
                          ? "Gasto · Finanzas"
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
                            Pagar cuota
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
    </>
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
