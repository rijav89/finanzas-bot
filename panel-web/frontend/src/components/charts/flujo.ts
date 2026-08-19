import type { DashboardResumen } from "@/api/types";

/** Colores de serie, en el orden del mockup. */
export const SERIES = [
  "var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)",
  "var(--s5)", "var(--s6)", "var(--s7)",
];

export interface Parte {
  id: string;
  valor: number;
}

export interface Flujo {
  origenes: Parte[];
  destinos: Parte[];
  total: number;
}

/** Cifras que no vale la pena dibujar: medio centavo no se ve ni suma. */
const EPSILON = 0.005;

/** De dónde salió la plata del mes y en qué se fue.
 *
 *  Lo calculan por igual el Sankey de escritorio y las barras de móvil: si cada uno
 *  armara su propia versión, tarde o temprano mostrarían cosas distintas.
 *
 *  Los orígenes suman siempre exactamente lo mismo que los destinos. Cuando gastaste
 *  más de lo que entró, la diferencia sale del "Saldo anterior"; cuando sobró, va a
 *  "Ahorro". Sin eso el total no cierra y alguna etiqueta termina mintiendo.
 */
export function calcularFlujo(datos: DashboardResumen): Flujo {
  const ingresos = Number(datos.ingresos_mes) || 0;
  const gastos = Number(datos.gastos_mes) || 0;
  const ahorro = Math.max(ingresos - gastos, 0);
  const delSaldo = Math.max(gastos - ingresos, 0);

  const catsGasto = [...datos.por_categoria]
    .sort((a, b) => Number(b.total) - Number(a.total))
    .slice(0, 5);
  const restoGasto = gastos - catsGasto.reduce((s, c) => s + Number(c.total), 0);

  const destinos: Parte[] = [
    ...(ahorro > EPSILON ? [{ id: "Ahorro", valor: ahorro }] : []),
    ...catsGasto.map((c) => ({ id: c.categoria, valor: Number(c.total) })),
    ...(restoGasto > EPSILON ? [{ id: "Otros gastos", valor: restoGasto }] : []),
  ];

  const origenes: Parte[] = [
    ...[...(datos.ingresos_por_categoria ?? [])]
      .map((c) => ({ id: etiquetaFuente(c.categoria), valor: Number(c.total) }))
      .filter((f) => f.valor > EPSILON)
      .sort((a, b) => b.valor - a.valor),
    ...(delSaldo > EPSILON ? [{ id: "Saldo anterior", valor: delSaldo }] : []),
  ];

  return {
    origenes,
    destinos,
    total: origenes.reduce((s, o) => s + o.valor, 0),
  };
}

/** 'Ingreso' es el valor por defecto del bot: como etiqueta suelta no dice nada. */
export function etiquetaFuente(categoria: string | null): string {
  return !categoria || categoria === "Ingreso" ? "Otros ingresos" : categoria;
}
