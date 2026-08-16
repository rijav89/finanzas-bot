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

export interface DashboardResumen {
  periodo: { anio: number; mes: number };
  saldo_total: number;
  saldos_por_cuenta: SaldoCuenta[];
  gastos_mes: number;
  ingresos_mes: number;
  por_categoria: CategoriaResumen[];
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

/** Las 14 del bot (bot/categorias.py) — mismo orden y grafía (sin tildes). */
export const CATEGORIAS = [
  "Comida", "Supermercado", "Transporte", "Servicios", "Salud",
  "Educacion", "Ropa", "Entretenimiento", "Tecnologia", "Finanzas",
  "Mascotas", "Belleza", "Hogar", "Otros",
] as const;

/** Origen del dinero que entra. 'Ingreso' es el default histórico del bot. */
export const CATEGORIAS_INGRESO = [
  "Sueldo", "Freelance", "Venta", "Regalo", "Reembolso", "Ingreso",
] as const;

// ── Módulos F4 ───────────────────────────────────────────────────────────────

export type Semaforo = "bien" | "atencion" | "critico" | "info";

export interface Categoria {
  id: number;
  nombre: string;
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
  transaccion_id: number | null;
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
