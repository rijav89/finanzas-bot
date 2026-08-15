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

export const CATEGORIAS = [
  "Comida", "Supermercado", "Transporte", "Servicios", "Salud",
  "Educacion", "Ropa", "Entretenimiento", "Tecnologia", "Finanzas",
  "Mascotas", "Belleza", "Hogar", "Otros",
] as const;
