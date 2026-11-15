import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { PublicLayout } from "../../components/layout";
import { AuthPage } from "../../pages/AuthPage";
import { HomePage } from "../../pages/HomePage";
import { NotFoundPage } from "../../pages/NotFoundPage";
import { PasswordResetConfirmPage } from "../../pages/PasswordResetConfirmPage";
import { PasswordResetRequestPage } from "../../pages/PasswordResetRequestPage";
import { SettingsPage } from "../../pages/SettingsPage";
import { CatalogPage } from "../../features/catalog/CatalogPage";
import { WorkoutDetailPage } from "../../features/catalog/WorkoutDetailPage";
import { ProfilePage } from "../../features/profile/ProfilePage";
import { ProgramDetailPage } from "../../features/programs/ProgramDetailPage";
import { ProgramsPage } from "../../features/programs/ProgramsPage";
import { RecommendationPage } from "../../features/programs/RecommendationPage";
import { Alert, Button, LoadingState } from "../../components/ui";
import { RequireAuth } from "./RequireAuth";

const CompositionEditorPage = lazy(() => import("../../features/programs/CompositionEditorPage").then((module) => ({ default: module.CompositionEditorPage })));
const CalendarPage = lazy(() => import("../../features/schedule/CalendarPage").then((module) => ({ default: module.CalendarPage })));
const SessionDetailPage = lazy(() => import("../../features/schedule/SessionDetailPage").then((module) => ({ default: module.SessionDetailPage })));
const NotificationsPage = lazy(() => import("../../features/notifications/NotificationsPage").then((module) => ({ default: module.NotificationsPage })));
const NotificationDetailPage = lazy(() => import("../../features/notifications/NotificationDetailPage").then((module) => ({ default: module.NotificationDetailPage })));
const CompletionFormPage = lazy(() => import("../../features/execution/CompletionFormPage").then((module) => ({ default: module.CompletionFormPage })));
const CompletionResultPage = lazy(() => import("../../features/execution/CompletionResultPage").then((module) => ({ default: module.CompletionResultPage })));

function PublicOnly({ mode }: { mode: "login" | "register" }) {
  const { account, status, error, refresh } = useAuth();
  if (status === "authenticated" && account) return <Navigate to="/" replace />;
  if (status === "loading") return <LoadingState text="Перевіряємо сесію…" />;
  if (status === "error") return <><Alert tone="error">{error}</Alert><Button onClick={() => void refresh()}>Спробувати ще раз</Button></>;
  return <AuthPage mode={mode} />;
}

export function AppRouter() {
  return (
    <Suspense fallback={<LoadingState text="Завантажуємо сторінку…" />}><Routes>
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
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/catalog/workouts/:id" element={<WorkoutDetailPage />} />
        <Route path="/catalog/workouts/:id/complete" element={<CompletionFormPage />} />
        <Route path="/programs" element={<ProgramsPage />} />
        <Route path="/programs/recommendation" element={<RecommendationPage />} />
        <Route path="/programs/:id" element={<ProgramDetailPage />} />
        <Route path="/programs/:id/workouts/:entryId" element={<CompositionEditorPage />} />
        <Route path="/schedule" element={<CalendarPage />} />
        <Route path="/schedule/:id" element={<SessionDetailPage />} />
        <Route path="/schedule/:id/complete" element={<CompletionFormPage />} />
        <Route path="/completed/:id" element={<CompletionResultPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/notifications/:id" element={<NotificationDetailPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes></Suspense>
  );
}
