import {
  ArrowDownLeft,
  ArrowLeftRight,
  Briefcase,
  Bus,
  Clapperboard,
  Dumbbell,
  GraduationCap,
  HandCoins,
  Home,
  Landmark,
  Laptop,
  PawPrint,
  Pill,
  Shirt,
  ShoppingCart,
  Sparkles,
  Tag,
  UtensilsCrossed,
  Zap,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/cn";

/** Icono por categoría (mockup Movimientos: tile redondeado gris con glifo). */
const ICONOS: Record<string, LucideIcon> = {
  Comida: UtensilsCrossed,
  Supermercado: ShoppingCart,
  Transporte: Bus,
  Servicios: Zap,
  Salud: Pill,
  Educacion: GraduationCap,
  Ropa: Shirt,
  Entretenimiento: Clapperboard,
  Tecnologia: Laptop,
  Finanzas: Landmark,
  Mascotas: PawPrint,
  Belleza: Sparkles,
  Hogar: Home,
  Otros: Tag,
  Transferencia: ArrowLeftRight,
  // Ingresos
  Ingreso: ArrowDownLeft,
  Sueldo: Briefcase,
  Freelance: Laptop,
  Venta: HandCoins,
  Regalo: Sparkles,
  Reembolso: ArrowLeftRight,
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
