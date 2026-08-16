import { Flag, MoreHorizontal, PiggyBank, Plus, Target } from "lucide-react";
import { useState } from "react";

import { useAhorros, useCuentas, useDefinirMetaAhorro } from "@/api/queries";
import { HeaderMovil } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { BarraProgreso } from "@/components/ui/BarraProgreso";
import { Boton } from "@/components/ui/Boton";
import { Card, PageHeader } from "@/components/ui/Card";
import { Donut } from "@/components/ui/Donut";
import { Hoja } from "@/components/ui/Hoja";
import { money } from "@/lib/money";

const COLORES = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s6)", "var(--s5)"];

export default function Ahorros() {
  const { data, isPending } = useAhorros();
  const { data: cuentas } = useCuentas();
  const [editando, setEditando] = useState<number | null>(null);

  const conMeta = (data?.items ?? []).filter((a) => a.meta);
  const totalMetas = conMeta.reduce((s, a) => s + (a.meta?.monto_objetivo ?? 0), 0);
  const acumulado = data?.total_ahorrado ?? 0;
  const pctGeneral = totalMetas > 0 ? (acumulado / totalMetas) * 100 : 0;

  const candidatas = (cuentas ?? []).filter(
    (c) => !(data?.items ?? []).some((a) => a.cuenta_id === c.id),
  );

  return (
    <>
      <HeaderMovil titulo="Ahorros" subtitulo={`${conMeta.length} metas activas`} />
      <div className="hidden lg:block">
        <PageHeader
          titulo="Ahorros"
          subtitulo={`${conMeta.length} metas activas · ${money(acumulado)} acumulados`}
          acciones={
            <Boton onClick={() => setEditando(candidatas[0]?.id ?? null)}>
              <Plus size={18} />
              Nueva meta
            </Boton>
          }
        />
      </div>

      {isPending && <div className="h-32 animate-pulse rounded-2xl bg-card" />}

      {data && (
        <>
          {/* Progreso general */}
          <Card className="mb-4">
            <h2 className="font-semibold text-ink-2">Progreso general</h2>
            <div className="mt-3 flex flex-wrap items-end gap-x-10 gap-y-4">
              <div>
                <p className="text-sm text-ink-2">Acumulado</p>
                <p className="mt-1 text-[1.75rem] font-bold leading-none text-good-ink tnum">
                  {money(acumulado)}
                </p>
              </div>
              <div>
                <p className="text-sm text-ink-2">Suma de metas</p>
                <p className="mt-1 text-[1.75rem] font-bold leading-none tnum">
                  {money(totalMetas)}
                </p>
              </div>
              <div>
                <p className="text-sm text-ink-2">Te falta</p>
                <p className="mt-1 text-[1.75rem] font-bold leading-none text-ink-3 tnum">
                  {money(Math.max(totalMetas - acumulado, 0))}
                </p>
              </div>
              <div className="min-w-[14rem] flex-1">
                <div className="mb-2 flex items-center justify-end gap-2">
                  <span className="text-sm text-ink-2 tnum">
                    {Math.round(pctGeneral)}% del total de tus metas
                  </span>
                  <Badge tono={pctGeneral >= 100 ? "good" : "good"}>
                    {pctGeneral >= 100 ? "Completado" : "En camino"}
                  </Badge>
                </div>
                <BarraProgreso porcentaje={pctGeneral} tono="good" />
              </div>
            </div>
          </Card>

          {/* Metas */}
          {conMeta.length > 0 && (
            <div className="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {conMeta.map((a, i) => (
                <Card key={a.cuenta_id}>
                  <div className="flex items-start gap-2">
                    <h3 className="min-w-0 flex-1 truncate font-semibold">{a.nombre}</h3>
                    <button
                      onClick={() => setEditando(a.cuenta_id)}
                      aria-label={`Editar meta de ${a.nombre}`}
                      className="-mr-1 -mt-1 flex size-8 items-center justify-center rounded-lg text-ink-3 hover:text-ink"
                    >
                      <MoreHorizontal size={18} />
                    </button>
                  </div>

                  <div className="mt-3 flex items-center gap-4">
                    <div className="relative shrink-0">
                      <Donut
                        porcentaje={a.meta!.porcentaje}
                        color={COLORES[i % COLORES.length]}
                      />
                      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold tnum">
                        {Math.round(a.meta!.porcentaje)}%
                      </span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-ink-2">Llevás</p>
                      <p className="text-2xl font-bold leading-tight tnum">{money(a.saldo)}</p>
                      <p className="mt-1 truncate text-sm text-ink-3 tnum">
                        Meta {money(a.meta!.monto_objetivo)}
                      </p>
                      <p className="mt-1.5 inline-flex items-center gap-1.5 text-sm text-ink-2">
                        <Flag size={14} className="shrink-0" />
                        {a.meta!.cumplida
                          ? "Meta alcanzada"
                          : `Te falta ${money(a.meta!.falta ?? 0)}`}
                      </p>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {conMeta.length === 0 && (
            <Card className="mb-4 py-10 text-center">
              <PiggyBank size={30} className="mx-auto text-ink-3" />
              <p className="mt-3 font-semibold">Todavía no tenés metas de ahorro</p>
              <p className="mt-1 text-sm text-ink-3">
                Asigná una meta a cualquier cuenta para empezar a seguirla.
              </p>
            </Card>
          )}

          {/* Convertir cuenta */}
          {candidatas.length > 0 && (
            <Card>
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="font-semibold text-ink-2">Convertir una cuenta en ahorro</h2>
                <p className="ml-auto text-sm text-ink-3">
                  Cualquier cuenta existente puede tener una meta
                </p>
              </div>
              <ConvertirCuenta cuentas={candidatas} />
            </Card>
          )}
        </>
      )}

      {editando !== null && (
        <FormMeta cuentaId={editando} onCerrar={() => setEditando(null)} />
      )}
    </>
  );
}

function ConvertirCuenta({ cuentas }: { cuentas: { id: number; nombre: string }[] }) {
  const definir = useDefinirMetaAhorro();
  const [cuentaId, setCuentaId] = useState(String(cuentas[0]?.id ?? ""));
  const [monto, setMonto] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!(Number(monto) > 0) || !cuentaId) return;
        definir.mutate(
          { cuentaId: Number(cuentaId), monto_objetivo: monto },
          { onSuccess: () => setMonto("") },
        );
      }}
      className="mt-4 flex flex-wrap items-end gap-3"
    >
      <label className="min-w-[12rem] flex-1">
        <span className="mb-1.5 block text-sm text-ink-2">Cuenta</span>
        <select
          value={cuentaId}
          onChange={(e) => setCuentaId(e.target.value)}
          className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent"
        >
          {cuentas.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre}
            </option>
          ))}
        </select>
      </label>

      <label className="min-w-[12rem] flex-1">
        <span className="mb-1.5 block text-sm text-ink-2">Meta a alcanzar</span>
        <div className="flex items-center gap-2 rounded-xl bg-card-soft px-3.5 focus-within:ring-2 focus-within:ring-accent">
          <span className="text-ink-3">$</span>
          <input
            inputMode="decimal"
            value={monto}
            onChange={(e) => setMonto(e.target.value.replace(/[^\d.]/g, ""))}
            placeholder="2,000.00"
            className="h-12 min-w-0 flex-1 bg-transparent text-sm outline-none tnum"
          />
        </div>
      </label>

      <Boton type="submit" disabled={!(Number(monto) > 0) || definir.isPending}>
        <Target size={17} />
        Asignar meta
      </Boton>
    </form>
  );
}

function FormMeta({ cuentaId, onCerrar }: { cuentaId: number; onCerrar: () => void }) {
  const definir = useDefinirMetaAhorro();
  const [monto, setMonto] = useState("");
  const [fecha, setFecha] = useState("");

  return (
    <Hoja titulo="Meta de ahorro" onCerrar={onCerrar} ancho="max-w-md">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!(Number(monto) > 0)) return;
          definir.mutate(
            {
              cuentaId,
              monto_objetivo: monto,
              ...(fecha ? { fecha_objetivo: fecha } : {}),
            },
            { onSuccess: onCerrar },
          );
        }}
        className="space-y-4"
      >
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium">¿Cuánto querés juntar?</span>
          <div className="flex items-center gap-2 rounded-xl bg-card-soft px-3.5 focus-within:ring-2 focus-within:ring-accent">
            <span className="text-xl text-ink-3">$</span>
            <input
              autoFocus
              inputMode="decimal"
              value={monto}
              onChange={(e) => setMonto(e.target.value.replace(/[^\d.]/g, ""))}
              placeholder="0.00"
              className="h-14 min-w-0 flex-1 bg-transparent text-xl font-bold outline-none tnum"
            />
          </div>
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium">¿Para cuándo? (opcional)</span>
          <input
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
            className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none [color-scheme:inherit] focus:ring-2 focus:ring-accent"
          />
        </label>

        {definir.isError && (
          <p role="alert" className="text-sm font-medium text-bad-ink">
            No se pudo guardar la meta.
          </p>
        )}

        <div className="flex gap-3 pt-1">
          <Boton type="button" variante="secundario" className="flex-1" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton
            type="submit"
            className="flex-[2]"
            disabled={!(Number(monto) > 0) || definir.isPending}
          >
            {definir.isPending ? "Guardando…" : "Guardar meta"}
          </Boton>
        </div>
      </form>
    </Hoja>
  );
}
