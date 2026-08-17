import {
  ArrowDownLeft,
  ArrowLeftRight,
  Briefcase,
  Building2,
  Bus,
  Car,
  Clapperboard,
  Dumbbell,
  FileText,
  Gift,
  GraduationCap,
  HandCoins,
  Home,
  Landmark,
  Laptop,
  PawPrint,
  Pill,
  Repeat,
  Shirt,
  ShoppingCart,
  Sparkles,
  Store,
  Tag,
  TrendingUp,
  UtensilsCrossed,
  Zap,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/cn";

/** Icono por categoría (mockup Movimientos: tile redondeado gris con glifo). */
const ICONOS: Record<string, LucideIcon> = {
  Comida: UtensilsCrossed,
  Supermercado: ShoppingCart,
  Vivienda: Building2,
  Servicios: Zap,
  "Transporte y vehiculo": Car,
  Salud: Pill,
  Educacion: GraduationCap,
  Ropa: Shirt,
  Entretenimiento: Clapperboard,
  Suscripciones: Repeat,
  Tecnologia: Laptop,
  Finanzas: Landmark,
  Mascotas: PawPrint,
  Belleza: Sparkles,
  Hogar: Home,
  Regalos: Gift,
  Impuestos: FileText,
  Otros: Tag,
  Transferencia: ArrowLeftRight,
  // Nombres anteriores: quedan mapeados por los movimientos históricos
  Transporte: Bus,
  Ingreso: ArrowDownLeft,
  // Ingresos
  Sueldo: Briefcase,
  Freelance: Laptop,
  Negocio: Store,
  "Regalo recibido": Gift,
  Reembolso: ArrowLeftRight,
  Intereses: TrendingUp,
  "Otros ingresos": HandCoins,
  Gimnasio: Dumbbell,
};

export function iconoCategoria(nombre: string | null | undefined): LucideIcon {
  return ICONOS[nombre ?? ""] ?? Tag;
}

/** Tile cuadrado redondeado que envuelve el icono; verde suave para ingresos. */
export function IconoTile({
  categoria,
  ingreso = false,
  tamano = "size-11",
}: {
  categoria: string | null | undefined;
  ingreso?: boolean;
  tamano?: string;
}) {
  const Icono = iconoCategoria(categoria);
  return (
    <span
      aria-hidden
      className={cn(
        "flex shrink-0 items-center justify-center rounded-xl",
        tamano,
        ingreso ? "bg-good-soft text-good-ink" : "bg-card-soft text-ink-2",
      )}
    >
      <Icono size={19} />
    </span>
  );
}
