import { ArrowLeft, MessageCircle, WalletCards } from "lucide-react";
import { useState } from "react";

import { ApiError } from "@/api/client";
import { useRegistrar } from "@/api/queries";
import { Boton } from "@/components/ui/Boton";
import { Card } from "@/components/ui/Card";

const MENSAJES: Record<string, string> = {
  codigo_invalido_o_expirado:
    "Ese código no es válido o ya venció. Pedí uno nuevo con /vincular en el bot: duran 10 minutos.",
  telegram_ya_vinculado:
    "Esa cuenta de Telegram ya tiene un panel. Iniciá sesión, o usá /vincular quitar en el bot para enlazar otra.",
  correo_ya_registrado: "Ya existe una cuenta con ese correo. Probá iniciando sesión.",
  alta_rechazada: "Supabase rechazó el alta. Revisá el correo y que la contraseña tenga 8 caracteres o más.",
  payload_invalido: "Revisá los datos: la contraseña necesita al menos 8 caracteres.",
};

/** Alta de un usuario nuevo del panel.
 *
 *  La puerta es el código que da el bot, no un registro abierto: quien no usa el bot
 *  no tiene nada que ver acá, y así nadie de internet puede crearse cuentas sueltas.
 *  Como la confirmación por correo está desactivada, al terminar queda con sesión
 *  iniciada y ya vinculado — sin segundo paso.
 */
export default function Registro({ onVolver }: { onVolver: () => void }) {
  const [codigo, setCodigo] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const registrar = useRegistrar();

  const mensajeError =
    registrar.error instanceof ApiError
      ? (MENSAJES[registrar.error.codigo] ?? "No se pudo crear la cuenta.")
      : registrar.error
        ? "No se pudo conectar con el servidor."
        : null;

  const valido = codigo.trim().length >= 6 && email.includes("@") && password.length >= 8;

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-accent text-white">
            <WalletCards size={20} />
          </span>
          <span className="text-xl font-bold tracking-tight">Fondo</span>
        </div>

        <Card padding="p-6">
          <h1 className="text-xl font-bold tracking-tight">Creá tu cuenta</h1>
          <p className="mt-1 text-sm text-ink-2">
            Tus datos ya están en el bot: esto solo les agrega un panel para verlos.
          </p>

          <div className="mt-4 flex gap-3 rounded-xl bg-accent-soft p-3.5">
            <MessageCircle size={18} className="mt-0.5 shrink-0 text-accent-ink" />
            <p className="text-sm text-accent-ink">
              Escribí <strong>/vincular</strong> en el bot de Telegram y pegá acá el código
              que te responde. Vence a los 10 minutos.
            </p>
          </div>

          <form
            className="mt-5 space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (valido) registrar.mutate({ email, password, codigo: codigo.trim() });
            }}
          >
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium">Código del bot</span>
              <input
                required
                autoFocus
                value={codigo}
                onChange={(e) => setCodigo(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))}
                maxLength={16}
                placeholder="A1B2C3D4"
                className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-center text-lg font-bold tracking-[0.2em] outline-none focus:ring-2 focus:ring-accent"
              />
            </label>

            <label className="block">
              <span className="mb-1.5 block text-sm font-medium">Correo</span>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent"
              />
            </label>

            <label className="block">
              <span className="mb-1.5 block text-sm font-medium">Contraseña</span>
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent"
              />
              <span className="mt-1.5 block text-xs text-ink-3">Mínimo 8 caracteres.</span>
            </label>

            {mensajeError && (
              <p role="alert" className="text-sm font-medium text-bad-ink">
                {mensajeError}
              </p>
            )}

            <Boton type="submit" className="w-full" disabled={!valido || registrar.isPending}>
              {registrar.isPending ? "Creando…" : "Crear cuenta y entrar"}
            </Boton>
          </form>

          <button
            onClick={onVolver}
            className="mt-4 flex w-full items-center justify-center gap-1.5 text-sm font-medium text-ink-2 hover:text-ink"
          >
            <ArrowLeft size={15} />
            Ya tengo cuenta
          </button>
        </Card>
      </div>
    </main>
  );
}
