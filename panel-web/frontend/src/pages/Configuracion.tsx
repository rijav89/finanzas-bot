import { Archive, Lock, Pencil, Plus, RotateCcw } from "lucide-react";
import { useState } from "react";

import {
  useArchivarCategoria,
  useCategorias,
  useCrearCategoria,
  useEditarCategoria,
} from "@/api/queries";
import type { Categoria } from "@/api/types";
import { HeaderMovil } from "@/components/layout/AppShell";
import { SelectorTema } from "@/components/layout/MenuCuenta";
import { Badge } from "@/components/ui/Badge";
import { Boton } from "@/components/ui/Boton";
import { Card, PageHeader } from "@/components/ui/Card";
import { Hoja } from "@/components/ui/Hoja";
import { cn } from "@/lib/cn";
import { IconoTile } from "@/lib/iconos";

type Tipo = "gasto" | "ingreso";

/** Mismos tonos que las series de los gráficos, para que una categoría propia
 *  no desentone con el resto del panel. */
const PALETA = ["#5b4fe8", "#0d9488", "#d97706", "#e11d48", "#0284c7", "#8b5cf6", "#15803d"];

export default function Configuracion() {
  const [tipo, setTipo] = useState<Tipo>("gasto");
  const [creando, setCreando] = useState(false);
  const { data: categorias, isPending } = useCategorias({ tipo, incluirArchivadas: true });

  const lista = categorias ?? [];
  const sistema = lista.filter((c) => c.es_sistema);
  const propias = lista.filter((c) => !c.es_sistema);

  return (
    <>
      <HeaderMovil titulo="Configuración" subtitulo="Categorías y apariencia" />
      <div className="hidden lg:block">
        <PageHeader
          titulo="Configuración"
          subtitulo="Personalizá tus categorías y el aspecto del panel"
          acciones={
            <Boton onClick={() => setCreando(true)}>
              <Plus size={18} />
              Nueva categoría
            </Boton>
          }
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <h2 className="font-semibold">Apariencia</h2>
          <p className="mt-1 text-sm text-ink-2">
            «Sistema» sigue la preferencia de tu teléfono o navegador.
          </p>
          <div className="mt-3">
            <SelectorTema />
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="font-semibold">Categorías</h2>
            <div className="ml-auto flex gap-1 rounded-xl bg-card-soft p-1">
              {(["gasto", "ingreso"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTipo(t)}
                  aria-pressed={tipo === t}
                  className={cn(
                    "h-9 rounded-lg px-3.5 text-sm font-semibold transition-colors",
                    tipo === t ? "bg-card text-ink shadow-sm" : "text-ink-2",
                  )}
                >
                  {t === "gasto" ? "Gastos" : "Ingresos"}
                </button>
              ))}
            </div>
          </div>

          {isPending ? (
            <div className="mt-4 space-y-2">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="h-14 animate-pulse rounded-xl bg-card-soft" />
              ))}
            </div>
          ) : (
            <>
              <Grupo
                titulo="Tuyas"
                vacio="Todavía no creaste categorías propias. Sirven para lo que las de sistema no cubren."
                items={propias}
              />
              <Grupo
                titulo="Del sistema"
                nota="Las comparte el bot de Telegram, por eso no se editan. Si alguna te estorba, creá la tuya."
                items={sistema}
              />
            </>
          )}

          <div className="mt-5 lg:hidden">
            <Boton className="w-full" onClick={() => setCreando(true)}>
              <Plus size={18} />
              Nueva categoría
            </Boton>
          </div>
        </Card>
      </div>

      {creando && <FormCategoria tipo={tipo} onCerrar={() => setCreando(false)} />}
    </>
  );
}

function Grupo({
  titulo,
  nota,
  vacio,
  items,
}: {
  titulo: string;
  nota?: string;
  vacio?: string;
  items: Categoria[];
}) {
  return (
    <section className="mt-5">
      <h3 className="text-[11px] font-semibold tracking-[0.08em] text-ink-3">
        {titulo.toUpperCase()}
      </h3>
      {nota && <p className="mt-1 text-sm text-ink-3">{nota}</p>}

      {items.length === 0 ? (
        vacio && <p className="mt-2 text-sm text-ink-3">{vacio}</p>
      ) : (
        <ul className="mt-2 divide-y divide-hairline">
          {items.map((c) => (
            <Fila key={c.id} categoria={c} />
          ))}
        </ul>
      )}
    </section>
  );
}

function Fila({ categoria }: { categoria: Categoria }) {
  const editar = useEditarCategoria();
  const archivar = useArchivarCategoria();
  const archivada = !categoria.activa;

  function renombrar() {
    const nombre = window.prompt(
      "Nuevo nombre de la categoría\n\nLos movimientos ya registrados se actualizan solos.",
      categoria.nombre,
    );
    if (nombre?.trim() && nombre.trim() !== categoria.nombre) {
      editar.mutate(
        { id: categoria.id, nombre: nombre.trim() },
        {
          onError: () =>
            window.alert("Ya existe una categoría con ese nombre."),
        },
      );
    }
  }

  return (
    <li className={cn("flex items-center gap-3 py-2.5", archivada && "opacity-55")}>
      <IconoTile categoria={categoria.nombre} tamano="size-9" />
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2">
          <span className="truncate font-medium">{categoria.nombre}</span>
          {categoria.color && (
            <span
              aria-hidden
              className="size-2.5 shrink-0 rounded-full"
              style={{ background: categoria.color }}
            />
          )}
        </span>
        {archivada && <span className="text-xs text-ink-3">Archivada</span>}
      </span>

      {categoria.es_sistema ? (
        <Badge tono="neutro">
          <Lock size={12} />
          Sistema
        </Badge>
      ) : archivada ? (
        <button
          onClick={() => editar.mutate({ id: categoria.id, activa: true })}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-accent"
        >
          <RotateCcw size={15} />
          Reactivar
        </button>
      ) : (
        <div className="flex items-center gap-3">
          <button
            onClick={renombrar}
            aria-label={`Renombrar ${categoria.nombre}`}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-2 hover:text-ink"
          >
            <Pencil size={15} />
            <span className="hidden sm:inline">Renombrar</span>
          </button>
          <button
            onClick={() => archivar.mutate(categoria.id)}
            aria-label={`Archivar ${categoria.nombre}`}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-2 hover:text-ink"
          >
            <Archive size={15} />
            <span className="hidden sm:inline">Archivar</span>
          </button>
        </div>
      )}
    </li>
  );
}

function FormCategoria({ tipo, onCerrar }: { tipo: Tipo; onCerrar: () => void }) {
  const crear = useCrearCategoria();
  const [nombre, setNombre] = useState("");
  const [color, setColor] = useState(PALETA[0]);

  return (
    <Hoja
      titulo={tipo === "gasto" ? "Nueva categoría de gasto" : "Nueva categoría de ingreso"}
      onCerrar={onCerrar}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!nombre.trim()) return;
          crear.mutate({ nombre: nombre.trim(), tipo, color }, { onSuccess: onCerrar });
        }}
        className="space-y-4"
      >
        <label className="block">
          <span className="mb-1.5 block text-sm font-medium">Nombre</span>
          <input
            autoFocus
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder={tipo === "gasto" ? "Gimnasio, Guardería…" : "Alquiler cobrado, Propinas…"}
            maxLength={40}
            className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent"
          />
        </label>

        <div>
          <span className="mb-1.5 block text-sm font-medium">Color</span>
          <div className="flex flex-wrap gap-2">
            {PALETA.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                aria-label={`Color ${c}`}
                aria-pressed={color === c}
                className={cn(
                  "size-9 rounded-full transition-transform",
                  color === c && "scale-110 ring-2 ring-accent ring-offset-2 ring-offset-[var(--card)]",
                )}
                style={{ background: c }}
              />
            ))}
          </div>
        </div>

        <p className="text-sm text-ink-3">
          El bot de Telegram sigue clasificando con las categorías de sistema: las tuyas se
          usan cuando registrás desde el panel.
        </p>

        {crear.isError && (
          <p role="alert" className="text-sm font-medium text-bad-ink">
            No se pudo crear (¿ya existe una con ese nombre?).
          </p>
        )}

        <div className="flex gap-3 pt-1">
          <Boton type="button" variante="secundario" className="flex-1" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" className="flex-[2]" disabled={!nombre.trim() || crear.isPending}>
            {crear.isPending ? "Creando…" : "Crear categoría"}
          </Boton>
        </div>
      </form>
    </Hoja>
  );
}
