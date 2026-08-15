const fmt = new Intl.NumberFormat("es-PE", {
  style: "currency",
  currency: "PEN",
  minimumFractionDigits: 2,
});

export function money(v: number | null | undefined): string {
  return fmt.format(v ?? 0);
}
