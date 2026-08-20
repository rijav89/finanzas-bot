import { WalletCards } from "lucide-react";
import { lazy, Suspense, useState } from "react";

import { ApiError } from "@/api/client";
import { useLogin } from "@/api/queries";
import { Boton } from "@/components/ui/Boton";
import { Card } from "@/components/ui/Card";

// El alta es la excepción, no el camino habitual: no vale la pena en el bundle inicial
const Registro = lazy(() => import("@/pages/Registro"));

const MENSAJES: Record<string, string> = {
  credenciales_invalidas: "Correo o contraseña incorrectos.",
  payload_invalido: "Revisá el correo ingresado.",
  db_unavailable: "La base de datos no está disponible. Intentá en un momento.",
};

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [creando, setCreando] = useState(false);
  const login = useLogin();

  // Login vive fuera del router (solo se monta sin sesión), así que el alta se
  // alterna con estado en vez de con una ruta.
  if (creando) {
    return (
      <Suspense fallback={null}>
        <Registro onVolver={() => setCreando(false)} />
      </Suspense>
    );
  }

  const mensajeError =
    login.error instanceof ApiError
      ? (MENSAJES[login.error.codigo] ?? "No se pudo iniciar sesión.")
      : login.error
        ? "No se pudo conectar con el servidor."
        : null;

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
          <h1 className="text-xl font-bold tracking-tight">Ingresá a tu panel</h1>
          <p className="mt-1 text-sm text-ink-2">Usá el correo con el que te registraste</p>

          <form
            className="mt-6 space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              login.mutate({ email, password });
            }}
          >
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
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-12 w-full rounded-xl bg-card-soft px-3.5 text-sm outline-none focus:ring-2 focus:ring-accent"
              />
            </label>

            {mensajeError && (
              <p role="alert" className="text-sm font-medium text-bad-ink">
                {mensajeError}
              </p>
            )}

            <Boton type="submit" className="w-full" disabled={login.isPending}>
              {login.isPending ? "Ingresando…" : "Ingresar"}
            </Boton>
          </form>

          <div className="mt-5 border-t border-hairline pt-4 text-center">
            <p className="text-sm text-ink-2">¿Usás el bot y todavía no tenés panel?</p>
            <button
              onClick={() => setCreando(true)}
              className="mt-1 text-sm font-semibold text-accent"
            >
              Creá tu cuenta con el código del bot
            </button>
          </div>
        </Card>
      </div>
    </main>
  );
}
