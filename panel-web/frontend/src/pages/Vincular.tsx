import { useState } from "react";

import { ApiError } from "@/api/client";
import { useLogout, useVincular } from "@/api/queries";
import { Boton } from "@/components/ui/Boton";
import { Card } from "@/components/ui/Card";

const MENSAJES: Record<string, string> = {
  codigo_invalido_o_expirado: "El código no existe o ya venció. Pide uno nuevo al bot.",
  ya_vinculado: "Esta cuenta web ya está vinculada.",
  telegram_ya_vinculado: "Ese usuario de Telegram ya está vinculado a otra cuenta web.",
};

export default function Vincular() {
  const [codigo, setCodigo] = useState("");
  const vincular = useVincular();
  const logout = useLogout();

  const mensajeError =
    vincular.error instanceof ApiError
      ? (MENSAJES[vincular.error.codigo] ?? "No se pudo vincular.")
      : vincular.error
        ? "No se pudo conectar con el servidor."
        : null;

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <h1 className="text-xl font-semibold">Vincula tu Telegram</h1>
        <p className="mt-2 text-sm text-ink-2">
          Escribe <span className="font-mono text-ink">/vincular</span> en el bot de Telegram y
          copia aquí el código que te dé.
        </p>

        <form
          className="mt-6 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            vincular.mutate({ codigo: codigo.trim() });
          }}
        >
          <input
            required
            value={codigo}
            onChange={(e) => setCodigo(e.target.value.toUpperCase())}
            placeholder="ABCD2345"
            maxLength={16}
            autoCapitalize="characters"
            className="w-full touch-44 rounded-xl bg-page px-3 text-center font-mono text-lg tracking-[0.3em] text-ink ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
          />

          {mensajeError && (
            <p role="alert" className="text-sm text-critical">
              {mensajeError}
            </p>
          )}

          <Boton type="submit" className="w-full" disabled={vincular.isPending}>
            {vincular.isPending ? "Vinculando…" : "Vincular"}
          </Boton>
        </form>

        <Boton
          variante="fantasma"
          className="mt-2 w-full"
          onClick={() => logout.mutate()}
        >
          Cerrar sesión
        </Boton>
      </Card>
    </main>
  );
}
