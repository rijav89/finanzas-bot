import { useState } from "react";

import { useLogin } from "@/api/queries";
import { ApiError } from "@/api/client";
import { Boton } from "@/components/ui/Boton";
import { Card } from "@/components/ui/Card";

const MENSAJES: Record<string, string> = {
  credenciales_invalidas: "Correo o contraseña incorrectos.",
  payload_invalido: "Revisa el correo ingresado.",
  db_unavailable: "La base de datos no está disponible. Intenta en un momento.",
};

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();

  const mensajeError =
    login.error instanceof ApiError
      ? (MENSAJES[login.error.codigo] ?? "No se pudo iniciar sesión.")
      : login.error
        ? "No se pudo conectar con el servidor."
        : null;

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <h1 className="text-xl font-semibold">FinanzasBot</h1>
        <p className="mt-1 text-sm text-ink-2">Ingresa a tu panel</p>

        <form
          className="mt-6 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            login.mutate({ email, password });
          }}
        >
          <label className="block">
            <span className="text-sm text-ink-2">Correo</span>
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full touch-44 rounded-xl bg-page px-3 text-ink ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
            />
          </label>

          <label className="block">
            <span className="text-sm text-ink-2">Contraseña</span>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full touch-44 rounded-xl bg-page px-3 text-ink ring-1 ring-[var(--border-ring)] outline-none focus:ring-2 focus:ring-accent"
            />
          </label>

          {mensajeError && (
            <p role="alert" className="text-sm text-critical">
              {mensajeError}
            </p>
          )}

          <Boton type="submit" className="w-full" disabled={login.isPending}>
            {login.isPending ? "Ingresando…" : "Ingresar"}
          </Boton>
        </form>
      </Card>
    </main>
  );
}
