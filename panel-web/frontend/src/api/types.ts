/** Tipos espejo de los schemas Pydantic del backend. */

export interface Me {
  email: string | null;
  auth_uid: string;
  vinculado: boolean;
  usuario_id: number | null;
}

export interface Cuenta {
  id: number;
  nombre: string;
  tipo: "corriente" | "ahorro";
  saldo_inicial: number | null;
  es_principal: boolean | null;
  activa: boolean | null;
}

export interface SaldoCuenta {
  cuenta_id: number;
  nombre: string;
  tipo: string;
  es_principal: boolean;
  saldo: number;
}

export interface CategoriaResumen {
  categoria: string;
  total: number;
  n: number;
}

export interface MovimientoReciente {
  id: number;
  tipo: "gasto" | "ingreso";
  monto: number;
  categoria: string | null;
  descripcion: string | null;
  fecha: string | null;
  cuenta: string | null;
}

/** Un punto del gráfico de tendencia: saldo al cierre de ese mes. */
export interface PuntoSaldo {
  mes: string;
  saldo: number;
}

export interface DashboardResumen {
  periodo: { anio: number; mes: number };
  saldo_total: number;
  saldos_por_cuenta: SaldoCuenta[];
  gastos_mes: number;
  ingresos_mes: number;
  por_categoria: CategoriaResumen[];
  /** Fuentes de ingreso del mes (Sueldo, Freelance…), origen del diagrama de flujo. */
  ingresos_por_categoria: CategoriaResumen[];
  ultimos_movimientos: MovimientoReciente[];
  tendencia_saldo: PuntoSaldo[];
  /** Promedio mensual de los meses previos; 0 = no hay con qué comparar. */
  promedio_previos: { gastos: number; ingresos: number; meses: number };
}

export interface Movimiento {
  id: number;
  tipo: "gasto" | "ingreso";
  monto: number;
  categoria: string | null;
  descripcion: string | null;
  medio: string | null;
  destinatario: string | null;
  fecha: string | null;
  cuenta_id: number | null;
}

export interface MovimientosPage {
  items: Movimiento[];
  limit: number;
  offset: number;
}

/** Respaldo por si el catálogo aún no cargó: el real vive en la tabla `categorias`
 *  y lo comparten el bot y el panel (bot/categorias.py tiene la misma grafía). */
export const CATEGORIAS = [
  "Comida", "Supermercado", "Vivienda", "Servicios", "Transporte y vehiculo",
  "Salud", "Educacion", "Ropa", "Entretenimiento", "Suscripciones",
  "Tecnologia", "Finanzas", "Mascotas", "Belleza", "Hogar",
  "Regalos", "Impuestos", "Otros",
] as const;

export const CATEGORIAS_INGRESO = [
  "Sueldo", "Freelance", "Negocio", "Regalo recibido",
  "Reembolso", "Intereses", "Otros ingresos",
] as const;

// ── Módulos F4 ───────────────────────────────────────────────────────────────

export type Semaforo = "bien" | "atencion" | "critico" | "info";

// ── Insights IA ──────────────────────────────────────────────────────────────

export type SeveridadInsight = "info" | "atencion" | "critico";

export interface Insight {
  id: number;
  tipo: "patron_gasto" | "alerta_presupuesto" | "tendencia" | "recomendacion";
  severidad: SeveridadInsight;
  titulo: string;
  detalle: string | null;
  categoria: string | null;
  metrica: string | null;
  delta_pct: number | null;
  periodo_inicio: string;
  periodo_fin: string;
  leido: boolean;
  creado_en: string;
}

export interface InsightsResp {
  items: Insight[];
  sin_leer: number;
  /** Null mientras el job semanal no haya corrido nunca. */
  generado_en: string | null;
}

export type TipoCategoria = "gasto" | "ingreso" | "ambos";

export interface Categoria {
  id: number;
  nombre: string;
  /** 'ambos' es solo Transferencia: aparece en los dos lados de un traslado. */
  tipo: TipoCategoria;
  icono: string | null;
  color: string | null;
  es_sistema: boolean;
  activa: boolean;
}

export interface PresupuestoItem {
  id: number;
  categoria: string;
  monto_limite: number;
  gastado: number;
  disponible: number;
  porcentaje: number;
  semaforo: Semaforo;
}

export interface PresupuestosResp {
  periodo: { anio: number; mes: number };
  items: PresupuestoItem[];
  total_limite: number;
  total_gastado: number;
  sin_presupuesto: { categoria: string; gastado: number }[];
}

export type TipoDeuda = "prestamo_recibido" | "prestamo_otorgado" | "tarjeta";

export interface Deuda {
  id: number;
  tipo: TipoDeuda;
  acreedor: string;
  monto_total: number;
  tasa_interes: number | null;
  num_cuotas: number | null;
  fecha_inicio: string;
  estado: "activa" | "pagada" | "cancelada";
  cuenta_id: number | null;
  /** Préstamo entre personas: se salda con montos sueltos, sin cronograma. */
  sin_cronograma: boolean;
  pagado: number;
  saldo_pendiente: number;
  porcentaje_pagado: number;
  cuotas_pendientes: number;
  proxima_cuota: { numero: number; monto: number; vence_en: string } | null;
}

export interface Cuota {
  numero: number;
  monto: number;
  vence_en: string;
  pagada: boolean;
  /** Solo uno de los dos: pagar genera un gasto, cobrar genera un ingreso. */
  transaccion_id: number | null;
  ingreso_id: number | null;
}

export interface DeudasResp {
  items: Deuda[];
  total_pendiente: number;
  debo: number;
  me_deben: number;
}

export interface Ahorro {
  cuenta_id: number;
  nombre: string;
  saldo: number;
  meta: {
    monto_objetivo: number;
    fecha_objetivo: string | null;
    porcentaje: number;
    falta: number | null;
    cumplida: boolean;
  } | null;
}

export interface Recurrente {
  id: number;
  descripcion: string;
  monto: number;
  dia_mes: number;
  categoria: string | null;
  cuenta_id: number | null;
  frecuencia: "mensual" | "semanal" | "anual";
  fecha_fin: string | null;
  activo: boolean;
  proximo_vencimiento: string;
}

export const ETIQUETA_TIPO_DEUDA: Record<TipoDeuda, string> = {
  prestamo_recibido: "Préstamo recibido",
  prestamo_otorgado: "Préstamo otorgado",
  tarjeta: "Tarjeta de crédito",
};
