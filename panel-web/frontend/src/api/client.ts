/** Wrapper de fetch: cookies HttpOnly, header CSRF, refresh automático en 401. */

export class ApiError extends Error {
  constructor(
    public status: number,
    public codigo: string,
  ) {
    super(codigo);
  }
}

type Json = Record<string, unknown> | undefined;

async function raw(path: string, method: string, body?: Json): Promise<Response> {
  return fetch(`/api/v1${path}`, {
    method,
    credentials: "include",
    headers: {
      "X-Requested-With": "fetch",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

let refreshEnCurso: Promise<boolean> | null = null;

async function intentarRefresh(): Promise<boolean> {
  refreshEnCurso ??= raw("/auth/refresh", "POST", {})
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      setTimeout(() => (refreshEnCurso = null), 0);
    });
  return refreshEnCurso;
}

export async function api<T = unknown>(
  path: string,
  opts: { method?: string; body?: Json } = {},
): Promise<T> {
  const method = opts.method ?? "GET";
  let res = await raw(path, method, opts.body);

  if (res.status === 401 && !path.startsWith("/auth/")) {
    if (await intentarRefresh()) {
      res = await raw(path, method, opts.body);
    }
  }

  const envelope = (await res.json().catch(() => ({}))) as {
    data?: T;
    error?: string | null;
  };

  if (!res.ok) {
    throw new ApiError(res.status, envelope.error ?? `http_${res.status}`);
  }
  return envelope.data as T;
}
