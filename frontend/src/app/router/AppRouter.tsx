import { Navigate, Route, Routes } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { PublicLayout } from "../../components/layout";
import { AuthPage } from "../../pages/AuthPage";
import { HomePage } from "../../pages/HomePage";
import { NotFoundPage } from "../../pages/NotFoundPage";
import { PasswordResetConfirmPage } from "../../pages/PasswordResetConfirmPage";
import { PasswordResetRequestPage } from "../../pages/PasswordResetRequestPage";
import { SettingsPage } from "../../pages/SettingsPage";
import { Alert, Button, LoadingState } from "../../components/ui";
import { RequireAuth } from "./RequireAuth";

function PublicOnly({ mode }: { mode: "login" | "register" }) {
  const { account, status, error, refresh } = useAuth();
  if (status === "authenticated" && account) return <Navigate to="/" replace />;
  if (status === "loading") return <LoadingState text="Перевіряємо сесію…" />;
  if (status === "error") return <><Alert tone="error">{error}</Alert><Button onClick={() => void refresh()}>Спробувати ще раз</Button></>;
  return <AuthPage mode={mode} />;
}

export function AppRouter() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/login" element={<PublicOnly mode="login" />} />
        <Route path="/register" element={<PublicOnly mode="register" />} />
        <Route path="/forgot-password" element={<PasswordResetRequestPage />} />
        <Route path="/password-reset" element={<PasswordResetRequestPage />} />
        <Route path="/reset-password/:uid/:token" element={<PasswordResetConfirmPage />} />
        <Route path="/reset-password" element={<PasswordResetConfirmPage />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
