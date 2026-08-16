/** Anillo de progreso de las metas de ahorro (mockup: 81% índigo, 39% teal, 50% ámbar). */
export function Donut({
  porcentaje,
  color = "var(--s1)",
  tamano = 96,
  grosor = 10,
}: {
  porcentaje: number;
  color?: string;
  tamano?: number;
  grosor?: number;
}) {
  const p = Math.min(Math.max(porcentaje, 0), 100);
  const radio = (tamano - grosor) / 2;
  const circ = 2 * Math.PI * radio;
  return (
    <svg
      width={tamano}
      height={tamano}
      viewBox={`0 0 ${tamano} ${tamano}`}
      role="img"
      aria-label={`${Math.round(p)}%`}
      className="-rotate-90"
    >
      <circle
        cx={tamano / 2}
        cy={tamano / 2}
        r={radio}
        fill="none"
        stroke="var(--card-soft)"
        strokeWidth={grosor}
      />
      <circle
        cx={tamano / 2}
        cy={tamano / 2}
        r={radio}
        fill="none"
        stroke={color}
        strokeWidth={grosor}
        strokeLinecap="round"
        strokeDasharray={`${(p / 100) * circ} ${circ}`}
      />
    </svg>
  );
}
