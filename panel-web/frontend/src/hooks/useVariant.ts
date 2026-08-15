import { useSyncExternalStore } from "react";

const QUERY = "(min-width: 1024px)";

function subscribe(cb: () => void) {
  const mq = window.matchMedia(QUERY);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}

/** 'full' en desktop (lg+), 'compact' en móvil/tablet. Un solo componente, dos densidades. */
export function useVariant(): "compact" | "full" {
  const esDesktop = useSyncExternalStore(
    subscribe,
    () => window.matchMedia(QUERY).matches,
    () => true,
  );
  return esDesktop ? "full" : "compact";
}
