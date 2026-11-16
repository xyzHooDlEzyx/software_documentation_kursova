import { useCallback, useEffect, useState, type DependencyList } from "react";

export type Resource<T> =
  | { status: "loading"; data: T | null; error: null }
  | { status: "ready"; data: T; error: null }
  | { status: "error"; data: T | null; error: unknown };

/**
 * Loads server state for a page. Responses that arrive after the inputs have
 * changed are ignored, so fast filter changes cannot show stale results.
 */
export function useResource<T>(load: () => Promise<T>, deps: DependencyList) {
  const [state, setState] = useState<Resource<T>>({ status: "loading", data: null, error: null });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setState((previous) => ({ status: "loading", data: previous.data, error: null }));
    load().then(
      (data) => {
        if (active) setState({ status: "ready", data, error: null });
      },
      (error: unknown) => {
        if (active) setState((previous) => ({ status: "error", data: previous.data, error }));
      },
    );
    return () => {
      active = false;
    };
    // `load` is recreated every render on purpose; `deps` lists what it reads.
  }, [...deps, version]);

  const reload = useCallback(() => setVersion((value) => value + 1), []);
  const setData = useCallback((data: T) => setState({ status: "ready", data, error: null }), []);
  return { ...state, reload, setData };
}
