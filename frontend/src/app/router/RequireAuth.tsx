import { useRef, useState } from "react";
import { Navigate, useLocation } from "react-router";

import { Alert, Button, LoadingState } from "../../components/ui";
import { AuthenticatedLayout } from "../../components/layout";
import { useAuth } from "../auth/AuthProvider";
import { ApiError } from "../api";

export function RequireAuth() {
  const { account, status, error, refresh, signOut, setAccount, setNotice } = useAuth();
  const location = useLocation();
  const [logoutBusy, setLogoutBusy] = useState(false);
  const completedLogout = useRef(false);

  if (status === "loading") return <LoadingState text="Перевіряємо сесію…" />;
  if (status === "error") return <div className="route-state"><Alert tone="error">{error}</Alert><Button onClick={() => void refresh()}>Спробувати ще раз</Button></div>;
  if (!account || status === "guest") return <Navigate to="/login" replace state={completedLogout.current ? { loggedOut: true } : { from: location }} />;

  async function onLogout() {
    setLogoutBusy(true);
    setNotice("");
    completedLogout.current = true;
    try {
      await signOut();
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) {
        setAccount(null);
      } else {
        completedLogout.current = false;
        setNotice(reason instanceof ApiError ? reason.message : "Не вдалося вийти з акаунта. Спробуйте ще раз.");
      }
    } finally { setLogoutBusy(false); }
  }

  return <AuthenticatedLayout account={account} onLogout={() => void onLogout()} logoutBusy={logoutBusy} />;
}
