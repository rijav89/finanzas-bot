import { useState } from "react";

import type { PuntoSaldo } from "@/api/types";
import { cn } from "@/lib/cn";
import { money } from "@/lib/money";

/** Área de saldo al cierre de cada mes.
 *
 *  SVG a mano, como el Donut: una sola curva no justifica traerse @nivo/line
 *  (~60 KB gz). El viewBox es 100x100 y se estira con preserveAspectRatio="none",
 *  así que los trazos llevan vector-effect para no deformarse; las etiquetas van
 *  fuera del SVG, en HTML, por la misma razón.
 */
export function LineaSaldo({ puntos }: { puntos: PuntoSaldo[] }) {
  const [activo, setActivo] = useState<number | null>(null);

  if (puntos.length < 2) {
    return (
      <p className="py-16 text-center text-sm text-ink-3">
        Cuando tengas un par de meses registrados verás acá cómo evoluciona tu saldo.
      </p>
    );
  }

  const valores = puntos.map((p) => Number(p.saldo));
  const max = Math.max(...valores, 0);
  const min = Math.min(...valores, 0);
  const rango = max - min || 1;

  const x = (i: number) => (i / (puntos.length - 1)) * 100;
  const y = (v: number) => 96 - ((v - min) / rango) * 92; // deja aire arriba y abajo

  const linea = valores.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(v)}`).join(" ");
  const area = `${linea} L 100 100 L 0 100 Z`;
  const cero = min < 0 ? y(0) : null;

  const seleccionado = activo ?? puntos.length - 1;
  const punto = puntos[seleccionado];
  const variacion = Number(punto.saldo) - valores[0];

  return (
    <div>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <p className="text-[2rem] font-bold leading-none tracking-tight tnum">
          {money(Number(punto.saldo))}
        </p>
        <p className="text-sm text-ink-2">
          <span className={cn("font-semibold", variacion >= 0 ? "text-good-ink" : "text-bad-ink")}>
            {variacion >= 0 ? "+" : ""}
            {money(variacion)}
          </span>{" "}
          desde {etiquetaMes(puntos[0].mes)}
        </p>
      </div>

      <div className="relative mt-4">
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="h-40 w-full overflow-visible"
          role="img"
          aria-label={`Saldo de los últimos ${puntos.length} meses`}
        >
          <defs>
            <linearGradient id="grad-saldo" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.28" />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
            </linearGradient>
          </defs>

          {cero !== null && (
            <line
              x1="0" y1={cero} x2="100" y2={cero}
              stroke="var(--bad-ink)" strokeWidth="1" strokeDasharray="3 3"
              vectorEffect="non-scaling-stroke" opacity="0.5"
            />
          )}

          <path d={area} fill="url(#grad-saldo)" />
          <path
            d={linea}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />
          <line
            x1={x(seleccionado)} y1="0" x2={x(seleccionado)} y2="100"
            stroke="var(--ring)" strokeWidth="1" vectorEffect="non-scaling-stroke"
          />
        </svg>

        {/* El punto va en HTML: dentro del SVG estirado saldría ovalado */}
        <span
          aria-hidden
          className="pointer-events-none absolute size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-card bg-accent"
          style={{
            left: `${x(seleccionado)}%`,
            top: `${y(Number(punto.saldo))}%`,
          }}
        />

        {/* Franjas invisibles: una por mes, para señalar con el mouse o el dedo */}
        <div className="absolute inset-0 flex">
          {puntos.map((p, i) => (
            <button
              key={p.mes}
              type="button"
              className="h-full flex-1 cursor-default"
              aria-label={`${etiquetaMes(p.mes)}: ${money(Number(p.saldo))}`}
              onMouseEnter={() => setActivo(i)}
              onFocus={() => setActivo(i)}
              onTouchStart={() => setActivo(i)}
              onMouseLeave={() => setActivo(null)}
              onBlur={() => setActivo(null)}
            />
          ))}
        </div>
      </div>

      <div className="mt-2 flex text-center text-xs">
        {puntos.map((p, i) => (
          <span
            key={p.mes}
            className={cn("flex-1", i === seleccionado ? "font-semibold text-ink" : "text-ink-3")}
          >
            {etiquetaMes(p.mes)}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Miniatura sin ejes ni interacción, para meter dentro de otra tarjeta.
 *
 *  En móvil no hay widget de tendencia, así que esta chispa dentro del saldo es la
 *  única forma de ver si la línea sube o baja.
 */
export function MiniLinea({ puntos }: { puntos: PuntoSaldo[] }) {
  if (puntos.length < 2) return null;

  const valores = puntos.map((p) => Number(p.saldo));
  const max = Math.max(...valores, 0);
  const min = Math.min(...valores, 0);
  const rango = max - min || 1;
  const x = (i: number) => (i / (puntos.length - 1)) * 100;
  const y = (v: number) => 94 - ((v - min) / rango) * 88;

  const linea = valores.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i)} ${y(v)}`).join(" ");

  return (
    <div className="mt-4">
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="h-11 w-full"
        role="img"
        aria-label={`Saldo de los últimos ${puntos.length} meses`}
      >
        <defs>
          <linearGradient id="grad-chispa" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.26" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${linea} L 100 100 L 0 100 Z`} fill="url(#grad-chispa)" />
        <path
          d={linea}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
      <div className="mt-1 flex justify-between text-[10.5px] text-ink-3">
        {puntos.map((p, i) => (
          <span key={p.mes} className={i === puntos.length - 1 ? "font-semibold text-ink-2" : ""}>
            {etiquetaMes(p.mes)}
          </span>
        ))}
      </div>
    </div>
  );
}

/** 'YYYY-MM-DD' se parsea como UTC con `new Date`, y en Lima (UTC-5) eso corre la
 *  etiqueta al mes anterior. Por eso se arma la fecha a mano en hora local. */
function etiquetaMes(iso: string): string {
  const [anio, mes] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, 1).toLocaleDateString("es-PE", { month: "short" });
}
