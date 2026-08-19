import { Download, FileSpreadsheet, FileText } from "lucide-react";
import { useState } from "react";

import { ApiError, descargar } from "@/api/client";
import { queryReporte, useCategorias, useCuentas, useReporte, type FiltrosReporte } from "@/api/queries";
import type { AgrupacionReporte } from "@/api/types";
import { HeaderMovil } from "@/components/layout/AppShell";
import { BarraProgreso } from "@/components/ui/BarraProgreso";
import { Boton } from "@/components/ui/Boton";
import { Card, PageHeader } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { money } from "@/lib/money";

const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

const AGRUPACIONES: { valor: AgrupacionReporte; etiqueta: string }[] = [
  { valor: "categoria", etiqueta: "Categoría" },
  { valor: "mes", etiqueta: "Mes" },
  { valor: "cuenta", etiqueta: "Cuenta" },
];

/** Atajos de rango: cubren casi todo sin obligar a elegir dos fechas. */
const RANGOS = [
  { id: "mes", etiqueta: "Este mes" },
  { id: "3m", etiqueta: "3 meses" },
  { id: "6m", etiqueta: "6 meses" },
  { id: "anio", etiqueta: "Este año" },
  { id: "custom", etiqueta: "Personalizado" },
] as const;

type RangoId = (typeof RANGOS)[number]["id"];

const iso = (d: Date) => d.toLocaleDateString("sv-SE");

function calcularRango(id: RangoId): { desde: string; hasta: string } {
  const hoy = new Date();
  const hasta = iso(hoy);
  if (id === "anio") return { desde: iso(new Date(hoy.getFullYear(), 0, 1)), hasta };
  if (id === "mes") return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth(), 1)), hasta };
  const meses = id === "3m" ? 2 : 5; // «3 meses» incluye el actual
  return { desde: iso(new Date(hoy.getFullYear(), hoy.getMonth() - meses, 1)), hasta };
}

export default function Reportes() {
  const [rango, setRango] = useState<RangoId>("mes");
  const [fechas, setFechas] = useState(() => calcularRango("mes"));
  const [groupBy, setGroupBy] = useState<AgrupacionReporte>("categoria");
  const [tipo, setTipo] = useState<"gasto" | "ingreso" | "">("");
  const [cuentaId, setCuentaId] = useState("");
  const [descargando, setDescargando] = useState<"xlsx" | "pdf" | null>(null);
  const [errorDescarga, setErrorDescarga] = useState<string | null>(null);

  const { data: cuentas } = useCuentas();
  const { data: categorias } = useCategorias();

  const filtros: FiltrosReporte = {
    ...fechas,
    group_by: groupBy,
    ...(tipo ? { tipo } : {}),
    ...(cuentaId ? { cuenta_id: Number(cuentaId) } : {}),
  };
  const { data, isPending, isError } = useReporte(filtros);

  function elegirRango(id: RangoId) {
    setRango(id);
    if (id !== "custom") setFechas(calcularRango(id));
  }

  async function bajar(formato: "xlsx" | "pdf") {
    if (descargando) return; // doble clic: el guardia del servidor es el que manda
    setDescargando(formato);
    setErrorDescarga(null);
    try {
      await descargar(
        `/reportes/export.${formato}?${queryReporte(filtros)}`,
        `finanzas.${formato}`,
      );
    } catch (e) {
      setErrorDescarga(mensajeDeError(e));
    } finally {
      setDescargando(null);
    }
  }

  const filas = data?.filas ?? [];
  const maximo = Math.max(...filas.map((f) => Math.max(f.gastos, f.ingresos)), 1);

  const acciones = (
    <>
      <Boton variante="secundario" disabled={descargando !== null} onClick={() => bajar("xlsx")}>
        <FileSpreadsheet size={17} />
        {descargando === "xlsx" ? "Generando…" : "Excel"}
      </Boton>
      <Boton variante="secundario" disabled={descargando !== null} onClick={() => bajar("pdf")}>
        <FileText size={17} />
        {descargando === "pdf" ? "Generando…" : "PDF"}
      </Boton>
    </>
  );

  return (
    <>
      <HeaderMovil titulo="Reportes" subtitulo="Filtrá, mirá y descargá" />
      <div className="hidden lg:block">
        <PageHeader
          titulo="Reportes"
          subtitulo="Tus movimientos agrupados como los necesites"
          acciones={acciones}
        />
      </div>

      {/* ── Filtros ── */}
      <Card className="mb-4">
        <div className="flex flex-wrap gap-2">
          {RANGOS.map((r) => (
            <button
              key={r.id}
              onClick={() => elegirRango(r.id)}
              aria-pressed={rango === r.id}
              className={cn(
                "h-10 rounded-full px-4 text-sm font-medium transition-colors",
                rango === r.id
                  ? "bg-accent-soft text-accent-ink ring-1 ring-accent/40"
                  : "bg-card-soft text-ink-2",
              )}
            >
              {r.etiqueta}
            </button>
          ))}
        </div>

        {rango === "custom" && (
          <div className="mt-3 grid grid-cols-2 gap-3">
            {(["desde", "hasta"] as const).map((campo) => (
              <label key={campo} className="block">
                <span className="mb-1.5 block text-sm font-medium capitalize">{campo}</span>
                <input
                  type="date"
                  value={fechas[campo]}
                  onChange={(e) => setFechas((f) => ({ ...f, [campo]: e.target.value }))}
                  className="h-11 w-full rounded-xl bg-card-soft px-3 text-sm outline-none [color-scheme:inherit] focus:ring-2 focus:ring-accent"
                />
              </label>
            ))}
          </div>
        )}

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Agrupar por</span>
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as AgrupacionReporte)}
              className="h-11 w-full rounded-xl bg-card-soft px-3 text-sm outline-none focus:ring-2 focus:ring-accent"
            >
              {AGRUPACIONES.map((a) => (
                <option key={a.valor} value={a.valor}>{a.etiqueta}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Tipo</span>
            <select
              value={tipo}
              onChange={(e) => setTipo(e.target.value as typeof tipo)}
              className="h-11 w-full rounded-xl bg-card-soft px-3 text-sm outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="">Gastos e ingresos</option>
              <option value="gasto">Solo gastos</option>
              <option value="ingreso">Solo ingresos</option>
            </select>
          </label>

          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">Cuenta</span>
            <select
              value={cuentaId}
              onChange={(e) => setCuentaId(e.target.value)}
              className="h-11 w-full rounded-xl bg-card-soft px-3 text-sm outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="">Todas</option>
              {(cuentas ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-4 flex gap-3 lg:hidden">{acciones}</div>
        {errorDescarga && (
          <p role="alert" className="mt-3 text-sm font-medium text-bad-ink">{errorDescarga}</p>
        )}
      </Card>

      {/* ── Totales ── */}
      {data && (
        <div className="mb-4 grid gap-4 sm:grid-cols-3">
          <Card>
            <p className="text-sm text-ink-2">Ingresos</p>
            <p className="mt-1.5 text-[1.75rem] font-bold leading-none text-good-ink tnum">
              {money(data.totales.ingresos)}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-ink-2">Gastos</p>
            <p className="mt-1.5 text-[1.75rem] font-bold leading-none text-bad-ink tnum">
              {money(data.totales.gastos)}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-ink-2">Neto · {data.totales.n} movimientos</p>
            <p className="mt-1.5 text-[1.75rem] font-bold leading-none tnum">
              {data.totales.neto >= 0 ? "+" : ""}
              {money(data.totales.neto)}
            </p>
          </Card>
        </div>
      )}

      {/* ── Tabla ── */}
      <Card padding="p-0">
        {isPending ? (
          <div className="space-y-2 p-5">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded-xl bg-card-soft" />
            ))}
          </div>
        ) : isError ? (
          <p className="p-6 text-sm text-bad-ink">
            No se pudo cargar el reporte. Revisá que el rango de fechas sea válido.
          </p>
        ) : filas.length === 0 ? (
          <p className="p-8 text-center text-sm text-ink-3">
            No hay movimientos en este período con esos filtros.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[34rem] text-sm">
              <thead>
                <tr className="border-b border-hairline text-left text-ink-2">
                  <th className="px-5 py-3 font-medium">
                    {AGRUPACIONES.find((a) => a.valor === groupBy)?.etiqueta}
                  </th>
                  <th className="px-5 py-3 text-right font-medium">Ingresos</th>
                  <th className="px-5 py-3 text-right font-medium">Gastos</th>
                  <th className="px-5 py-3 text-right font-medium">Neto</th>
                  <th className="px-5 py-3 text-right font-medium">Mov.</th>
                </tr>
              </thead>
              <tbody>
                {filas.map((f) => (
                  <tr key={f.clave} className="border-b border-hairline last:border-0">
                    <td className="px-5 py-3">
                      <span className="font-semibold">{etiquetaClave(f.clave, groupBy)}</span>
                      <BarraProgreso
                        className="mt-2 max-w-[13rem]"
                        altura="h-1.5"
                        porcentaje={(Math.max(f.gastos, f.ingresos) / maximo) * 100}
                        tono={f.ingresos > f.gastos ? "good" : "accent"}
                      />
                    </td>
                    <td className="px-5 py-3 text-right tnum">
                      {f.ingresos > 0 ? money(f.ingresos) : "—"}
                    </td>
                    <td className="px-5 py-3 text-right tnum">
                      {f.gastos > 0 ? money(f.gastos) : "—"}
                    </td>
                    <td
                      className={cn(
                        "px-5 py-3 text-right font-semibold tnum",
                        f.neto >= 0 ? "text-good-ink" : "text-bad-ink",
                      )}
                    >
                      {f.neto >= 0 ? "+" : ""}
                      {money(f.neto)}
                    </td>
                    <td className="px-5 py-3 text-right text-ink-3 tnum">{f.n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <p className="mt-4 flex items-center gap-2 text-sm text-ink-3">
        <Download size={15} />
        Los archivos traen este resumen más el detalle movimiento por movimiento.
        {categorias && ` Catálogo actual: ${categorias.length} categorías.`}
      </p>
    </>
  );
}

/** Cada rechazo del servidor tiene una causa distinta y una espera distinta. */
function mensajeDeError(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.codigo === "export_en_curso")
      return "Ya estás generando un archivo. Esperá a que termine ese antes de pedir otro.";
    if (e.codigo === "export_ocupado")
      return "El servidor está armando otro archivo en este momento. Probá de nuevo en unos segundos.";
    if (e.codigo === "rango_demasiado_largo")
      return "El rango es demasiado largo: el máximo son 5 años.";
  }
  return "No se pudo generar el archivo. Intentá de nuevo.";
}

/** Las claves de mes llegan como 'YYYY-MM' desde la base. */
function etiquetaClave(clave: string, groupBy: AgrupacionReporte): string {
  if (groupBy === "mes" && clave?.includes("-")) {
    const [anio, mes] = clave.split("-");
    return `${MESES[Number(mes) - 1]} ${anio}`;
  }
  return clave || "—";
}
