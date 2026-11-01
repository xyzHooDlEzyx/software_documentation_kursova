import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { ApiError, currentUser, initializeCsrf, logout, type Account } from "../api";

export type AuthStatus = "loading" | "authenticated" | "guest" | "error";

type AuthContextValue = {
  account: Account | null;
  status: AuthStatus;
  error: string;
  notice: string;
  setNotice: (notice: string) => void;
  refresh: () => Promise<void>;
  setAccount: (account: Account | null) => void;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function authErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  return "Не вдалося перевірити сесію. Спробуйте ще раз.";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [account, setAccountState] = useState<Account | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const requestVersion = useRef(0);

  const refresh = useCallback(async () => {
    const version = ++requestVersion.current;
    setStatus("loading");
    setError("");
    try {
      await initializeCsrf();
      const user = await currentUser();
      if (version !== requestVersion.current) return;
      setAccountState(user);
      setStatus("authenticated");
    } catch (reason) {
      if (version !== requestVersion.current) return;
      if (reason instanceof ApiError && reason.status === 401) {
        setAccountState(null);
        setStatus("guest");
      } else {
        setError(authErrorMessage(reason));
        setStatus("error");
      }
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const setAccount = useCallback((next: Account | null) => {
    requestVersion.current += 1;
    setAccountState(next);
    setStatus(next ? "authenticated" : "guest");
    setError("");
  }, []);

  const signOut = useCallback(async () => {
    await logout();
    setAccount(null);
  }, [setAccount]);

  const value = useMemo(() => ({ account, status, error, notice, setNotice, refresh, setAccount, signOut }), [account, status, error, notice, refresh, setAccount, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
