import { PiggyBank, Wallet } from "lucide-react";

import { useCuentas, useDashboard } from "@/api/queries";
import { Card } from "@/components/ui/Card";
import { money } from "@/lib/money";

export default function Cuentas() {
  const { data: cuentas, isPending } = useCuentas();
  const { data: dash } = useDashboard();

  const saldoDe = (id: number) =>
    dash?.saldos_por_cuenta.find((s) => s.cuenta_id === id)?.saldo;

  return (
    <>
      <h1 className="mb-4 text-xl font-semibold lg:text-2xl">Cuentas</h1>

      {isPending ? (
        <div className="space-y-2">
          {[0, 1].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-2xl bg-card" />
          ))}
        </div>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {(cuentas ?? []).map((c) => {
            const Icono = c.tipo === "ahorro" ? PiggyBank : Wallet;
            const saldo = saldoDe(c.id);
            return (
              <li key={c.id}>
                <Card className="flex items-center gap-3">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-page text-ink-2">
                    <Icono size={20} />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate font-medium">{c.nombre}</p>
                    <p className="text-xs text-ink-3">
                      {c.tipo === "ahorro" ? "Ahorro" : "Corriente"}
                      {c.es_principal && " · Principal"}
                    </p>
                  </div>
                  {saldo !== undefined && (
                    <span className="ml-auto shrink-0 font-medium tabular-nums">
                      {money(Number(saldo))}
                    </span>
                  )}
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
