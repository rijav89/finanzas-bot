/** Colores de serie para cuentas, categorías y desgloses, en el orden del mockup. */
export const SERIES = [
  "var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)",
  "var(--s5)", "var(--s6)", "var(--s7)",
];

export function colorSerie(i: number, desplazar = 0): string {
  return SERIES[(i + desplazar) % SERIES.length];
}
