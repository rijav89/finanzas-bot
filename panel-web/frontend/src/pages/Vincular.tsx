import { Bot } from "lucide-react";
import { useState } from "react";

import { ApiError } from "@/api/client";
import { useLogout, useVincular } from "@/api/queries";
import { Boton } from "@/components/ui/Boton";
import { Card } from "@/components/ui/Card";

const MENSAJES: Record<string, string> = {
  codigo_invalido_o_expirado: "El código no existe o ya venció. Pedí uno nuevo al bot.",
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
      <Card className="w-full max-w-sm" padding="p-6">
        <span className="flex size-12 items-center justify-center rounded-xl bg-accent-soft text-accent-ink">
          <Bot size={24} />
        </span>
        <h1 className="mt-4 text-xl font-bold tracking-tight">Vinculá tu Telegram</h1>
        <p className="mt-2 text-sm text-ink-2">
          Escribí <span className="font-semibold text-ink">/vincular</span> en el bot y copiá
          acá el código que te dé.
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
            className="h-14 w-full rounded-xl bg-card-soft text-center text-lg font-bold tracking-[0.3em] outline-none focus:ring-2 focus:ring-accent"
          />

          {mensajeError && (
            <p role="alert" className="text-sm font-medium text-bad-ink">
              {mensajeError}
            </p>
          )}

          <Boton type="submit" className="w-full" disabled={vincular.isPending}>
            {vincular.isPending ? "Vinculando…" : "Vincular"}
          </Boton>
        </form>

        <Boton variante="fantasma" className="mt-2 w-full" onClick={() => logout.mutate()}>
          Cerrar sesión
        </Boton>
      </Card>
    </main>
  );
}
