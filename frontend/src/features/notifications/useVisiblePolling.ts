import { useCallback, useEffect, useRef } from "react";

export function useVisiblePolling(refresh: () => void | Promise<void>, intervalMs = 60_000) {
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  const run = useCallback(() => { if (document.visibilityState === "visible") void refreshRef.current(); }, []);

  useEffect(() => {
    run();
    const timer = window.setInterval(run, intervalMs);
    const visibility = () => { if (document.visibilityState === "visible") run(); };
    window.addEventListener("focus", run);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", run);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, [intervalMs, run]);
}
