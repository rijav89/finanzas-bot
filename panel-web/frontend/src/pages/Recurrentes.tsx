import { Bot, CalendarClock, CalendarDays, MoreHorizontal, Plus } from "lucide-react";
import { useState } from "react";

import {
  useCategorias,
  useCrearRecurrente,
  useCuentas,
  useDashboard,
  useEditarRecurrente,
  useEliminarRecurrente,
  useRecurrentes,
} from "@/api/queries";
import { HeaderMovil } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { Boton } from "@/components/ui/Boton";
import { Card, PageHeader } from "@/components/ui/Card";
import { Hoja } from "@/components/ui/Hoja";
import { Toggle } from "@/components/ui/Toggle";
import { cn } from "@/lib/cn";
import { iconoCategoria } from "@/lib/iconos";
import { money } from "@/lib/money";

const FRECUENCIAS = [
  { valor: "mensual", etiqueta: "Cada mes" },
  { valor: "semanal", etiqueta: "Cada semana" },
  { valor: "anual", etiqueta: "Cada año" },
] as const;

export default function Recurrentes() {
  const { data, isPending } = useRecurrentes();
  const { data: dash } = useDashboard();
  const editar = useEditarRecurrente();
  const eliminar = useEliminarRecurrente();
  const [creando, setCreando] = useState(false);

  const items = data?.items ?? [];
  const ingresos = Number(dash?.ingresos_mes ?? 0);
  const pctIngresos =
    ingresos > 0 ? Math.round(((data?.total_mensual ?? 0) / ingresos) * 100) : null;

  const dias = items
    .map((p) => diasHasta(p.proximo_vencimiento))
    .filter((d) => d >= 0)
    .sort((a, b) => a - b);
  const proximo = dias[0];

  return (
    <>
      <HeaderMovil titulo="Recurrentes" subtitulo={`${items.length} activos`} />
      <div className="hidden lg:block">
        <PageHeader
          titulo="Recurrentes"
          subtitulo="Alquiler, servicios y suscripciones"
          acciones={
            <Boton onClick={() => setCreando(true)}>
              <Plus size={18} />
              Nuevo recurrente
            </Boton>
          }
        />
      </div>

      {isPending && <div className="h-32 animate-pulse rounded-2xl bg-card" />}

      {data && (
        <>
          <div className="mb-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_1.6fr]">
            <Card>
              <h2 className="font-semibold text-ink-2">Compromiso mensual</h2>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <p className="text-[2.25rem] font-bold leading-none tracking-tight tnum">
                  {money(data.total_mensual)}
                </p>
                {pctIngresos !== null && (
                  <Badge tono={pctIngresos > 50 ? "bad" : pctIngresos > 30 ? "warn" : "good"}>
                    {pctIngresos}% de tus ingresos
                  </Badge>
                )}
              </div>
              <p className="mt-3 text-sm text-ink-2">
                {items.length} recurrentes activos
                {proximo !== undefined &&
                  ` · el más próximo vence ${proximo === 0 ? "hoy" : `en ${proximo} días`}`}
              </p>
            </Card>

            <Card>
              <div className="flex items-start gap-4">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent-ink">
                  <Bot size={20} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">Te aviso el día que vence cada uno</p>
                  <p className="mt-1 text-sm text-ink-2">
                    Todo lo que cargues acá se convierte en un recordatorio del bot. Confirmás el
                    pago desde el chat y queda registrado como gasto.
                  </p>
                </div>
              </div>
            </Card>
          </div>

          <Card padding="p-0">
            <div className="flex flex-wrap items-center gap-2 px-5 py-4">
              <h2 className="font-semibold">Todos los recurrentes</h2>
              <p className="ml-auto text-sm text-ink-3">Ordenados por día de vencimiento</p>
            </div>

            {items.length === 0 ? (
              <div className="px-5 pb-10 pt-2 text-center">
                <CalendarClock size={30} className="mx-auto text-ink-3" />
                <p className="mt-3 font-semibold">Sin pagos recurrentes</p>
                <p className="mt-1 text-sm text-ink-3">
                  Anotá alquiler, servicios o suscripciones para no olvidarlos.
                </p>
              </div>
            ) : (
              <ul className="px-2 pb-2">
                {items.map((p) => {
                  const Icono = iconoCategoria(p.categoria);
                  const d = diasHasta(p.proximo_vencimiento);
                  return (
                    <li key={p.id}>
                      <div
                        className={cn(
                          "flex flex-wrap items-center gap-3 rounded-xl px-3 py-3.5 transition-colors hover:bg-card-soft",
                          !p.activo && "opacity-55",
                        )}
                      >
                        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-card-soft text-ink-2">
                          <Icono size={19} />
                        </span>

                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate font-semibold">{p.descripcion}</p>
                            {p.activo && d >= 0 && d <= 3 && (
                              <Badge tono="warn">
                                {d === 0 ? "Vence hoy" : `Vence en ${d} días`}
                              </Badge>
                            )}
                          </div>
                          <p className="mt-0.5 truncate text-sm text-ink-2">{p.categoria}</p>
                        </div>

                        <span className="hidden shrink-0 items-center gap-1.5 text-sm text-ink-2 sm:flex">
                          <CalendarDays size={15} />
                          {p.frecuencia === "mensual"
                            ? `Día ${p.dia_mes} de cada mes`
                            : FRECUENCIAS.find((f) => f.valor === p.frecuencia)?.etiqueta}
                        </span>

                        <span className="shrink-0 font-bold tnum">{money(p.monto)}</span>

                        <Toggle
                          activo={!!p.activo}
                          etiqueta={`Activar ${p.descripcion}`}
                          onChange={(v) => editar.mutate({ id: p.id, activo: v })}
                        />

                        <button
                          onClick={() => eliminar.mutate(p.id)}
                          aria-label={`Eliminar ${p.descripcion}`}
                          className="flex size-9 shrink-0 items-center justify-center rounded-lg text-ink-3 hover:text-ink"
                        >
                          <MoreHorizontal size={18} />
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>
        </>
      )}

      {creando && <FormRecurrente onCerrar={() => setCreando(false)} />}
    </>
  );
}

function diasHasta(iso: string): number {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const [a, m, d] = iso.split("-").map(Number);
  return Math.round((new Date(a, m - 1, d).getTime() - hoy.getTime()) / 86_400_000);
}

function FormRecurrente({ onCerrar }: { onCerrar: () => void }) {
  const { data: cuentas } = useCuentas();
  const { data: categorias } = useCategorias({ tipo: "gasto" });
  const crear = useCrearRecurrente();

  const [descripcion, setDescripcion] = useState("");
  const [monto, setMonto] = useState("");
  const [dia, setDia] = useState("1");
  const [categoria, setCategoria] = useState("Servicios");
  const [frecuencia, setFrecuencia] = useState<string>("mensual");
  const [cuentaId, setCuentaId] = useState("");

  const diaNum = Number(dia);
  const valido = descripcion.trim() && Number(monto) > 0 && diaNum >= 1 && diaNum <= 31;

  return (
    <Hoja titulo="Nuevo recurrente" onCerrar={onCerrar}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!valido) return;
          crear.mutate(
            {
              descripcion: descripcion.trim(),
              monto,
              dia_mes: diaNum,
              categoria,
              frecuencia,
              ...(cuentaId ? { cuenta_id: Number(cuentaId) } : {}),
            },
            { onSuccess: onCerrar },
          );
        }}
        className="space-y-4"
      >
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium">¿Qué pagás?</span>
          <input
            autoFocus
            value={descripcion}
            onChange={(e) => setDescripcion(e.target.value)}
            placeholder="Alquiler, Netflix, luz…"
            maxLength={200}
            className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent"
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Monto</span>
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
            <span className="mb-1.5 block text-sm font-medium">Día del mes</span>
            <input
              inputMode="numeric"
              value={dia}
              onChange={(e) => setDia(e.target.value.replace(/\D/g, "").slice(0, 2))}
              className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent tnum"
            />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Categoría</span>
            <select
              value={categoria}
              onChange={(e) => setCategoria(e.target.value)}
              className="h-12 w-full rounded-xl bg-card-soft px-3 text-sm outline-none focus:ring-2 focus:ring-accent"
            >
              {(categorias ?? [])
                .filter((c) => c.tipo !== "ambos")
                .map((c) => (
                  <option key={c.id} value={c.nombre}>
                    {c.nombre}
                  </option>
                ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Frecuencia</span>
            <select
              value={frecuencia}
              onChange={(e) => setFrecuencia(e.target.value)}
              className="h-12 w-full rounded-xl bg-card-soft px-3 text-sm outline-none focus:ring-2 focus:ring-accent"
            >
              {FRECUENCIAS.map((f) => (
                <option key={f.valor} value={f.valor}>
                  {f.etiqueta}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium">Cuenta (opcional)</span>
          <select
            value={cuentaId}
            onChange={(e) => setCuentaId(e.target.value)}
            className="h-12 w-full rounded-xl bg-card-soft px-3 text-sm outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="">Sin especificar</option>
            {(cuentas ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>

        {crear.isError && (
          <p role="alert" className="text-sm font-medium text-bad-ink">
            No se pudo crear el recurrente.
          </p>
        )}

        <div className="flex gap-3 pt-1">
          <Boton type="button" variante="secundario" className="flex-1" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" className="flex-[2]" disabled={!valido || crear.isPending}>
            {crear.isPending ? "Creando…" : "Crear"}
          </Boton>
        </div>
      </form>
    </Hoja>
  );
}
