import { useEffect, useState } from "react";
import { Link, NavLink } from "react-router";

import { listNotifications } from "./api";
import { useVisiblePolling } from "./useVisiblePolling";

export function useUnreadNotificationCount() {
  const [count, setCount] = useState(0);
  useVisiblePolling(async () => {
    try { setCount((await listNotifications({ status: "pending", pageSize: 1 })).count); }
    catch { /* Page-level requests surface errors; the navigation remains usable. */ }
  });
  useEffect(() => {
    const read = () => setCount((value) => Math.max(0, value - 1));
    window.addEventListener("notification-read", read);
    return () => window.removeEventListener("notification-read", read);
  }, []);
  return count;
}

function BellIcon({ className = "" }: { className?: string }) {
  return <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none"><path d="M6 9a6 6 0 0 1 12 0c0 7 3 7 3 8H3c0-1 3-1 3-8Zm4 11h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function CountBadge({ count, compact = false }: { count: number; compact?: boolean }) {
  if (count <= 0) return null;
  return <span className={`${compact ? "absolute right-0 top-0" : "ml-auto"} grid min-w-5 place-items-center rounded-chip bg-brand px-1 text-caption text-primary-foreground`} aria-live="polite">{count}</span>;
}

export function NotificationNavLink({ count, variant }: { count: number; variant: "header" | "sidebar" }) {
  const accessibleName = count ? `Сповіщення, непрочитаних: ${count}` : "Сповіщення";
  if (variant === "sidebar") {
    return <NavLink to="/notifications" aria-label={accessibleName} className={({ isActive }) => `flex min-h-11 min-w-0 items-center gap-space-3 rounded-field px-space-3 py-space-2 text-small font-semibold no-underline transition-colors duration-150 hover:bg-interactive-hover-state hover:text-foreground motion-reduce:transition-none ${isActive ? "bg-selected-state text-brand" : "text-muted-foreground"}`}>
      <BellIcon className="size-5 shrink-0" /><span>Сповіщення</span><CountBadge count={count} />
    </NavLink>;
  }
  return <Link to="/notifications" className="relative inline-flex min-h-11 items-center gap-space-2 rounded-field px-space-3 text-small font-semibold text-muted-foreground no-underline hover:bg-interactive-hover-state max-[480px]:px-space-2" aria-label={accessibleName}>
    <BellIcon className="size-5" /><span className="max-[480px]:sr-only">Сповіщення</span><CountBadge count={count} compact />
  </Link>;
}
