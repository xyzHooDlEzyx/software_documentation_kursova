import type { JSX } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";

import type { Account } from "../../app/api";
import { Button } from "../ui";
import { NotificationNavLink, useUnreadNotificationCount } from "../../features/notifications/NotificationNavLink";
import "./layout.css";

export type AuthenticatedLayoutProps = {
  account: Account;
  onLogout: () => void;
  logoutBusy?: boolean;
};

function FitnessMark({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none">
      <path d="M6.5 8v8M4 10v4m13.5-6v8M20 10v4M8 12h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function HomeIcon({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none">
      <path
        d="m3.5 10 8.5-7 8.5 7v10.5h-6v-6h-5v6h-6V10Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SettingsIcon({ className = "" }: { className?: string }) {
  // Lucide "settings" (ISC): outer contour and inner circle share the 12,12 centre.
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

type IconProps = { className?: string };
// Outline icons after Lucide (ISC licence), same 24px grid and stroke as the rest.
function LineIcon({ className = "", children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}
const ProgressIcon = ({ className }: IconProps) => (
  <LineIcon className={className}>
    <path d="M22 7l-8.5 8.5-5-5L2 17" />
    <path d="M16 7h6v6" />
  </LineIcon>
);
const StatsIcon = ({ className }: IconProps) => (
  <LineIcon className={className}>
    <path d="M3 3v16a2 2 0 0 0 2 2h16" />
    <path d="M18 17V9M13 17V5M8 17v-3" />
  </LineIcon>
);
const HistoryIcon = ({ className }: IconProps) => (
  <LineIcon className={className}>
    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
    <path d="M3 3v5h5M12 7v5l4 2" />
  </LineIcon>
);
const PointsIcon = ({ className }: IconProps) => (
  <LineIcon className={className}>
    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
  </LineIcon>
);
const AchievementIcon = ({ className }: IconProps) => (
  <LineIcon className={className}>
    <circle cx="12" cy="8" r="6" />
    <path d="M15.48 12.89 17 22l-5-3-5 3 1.52-9.11" />
  </LineIcon>
);
const ChallengeIcon = ({ className }: IconProps) => (
  <LineIcon className={className}>
    <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1zM4 22v-7" />
  </LineIcon>
);
const LeaderboardIcon = ({ className }: IconProps) => (
  <LineIcon className={className}>
    <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16" />
    <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
    <path d="M18 2H6v7a6 6 0 0 0 12 0V2z" />
  </LineIcon>
);
const MoreIcon = ({ className }: IconProps) => (
  <LineIcon className={className}>
    <circle cx="5" cy="12" r="1" />
    <circle cx="12" cy="12" r="1" />
    <circle cx="19" cy="12" r="1" />
  </LineIcon>
);

function ProfileIcon({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M4 20.5c1.4-3.6 4.4-5.5 8-5.5s6.6 1.9 8 5.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function CatalogIcon({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none">
      <path
        d="M4 5.5A1.5 1.5 0 0 1 5.5 4H10v16H5.5A1.5 1.5 0 0 1 4 18.5v-13ZM14 4h4.5A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5H14V4Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ProgramsIcon({ className = "" }: { className?: string }) {
  // Clipboard with a checklist, so it differs from the schedule calendar.
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="8" y="2.5" width="8" height="4" rx="1" />
      <path d="M16 4.5h2a2 2 0 0 1 2 2V20a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2h2M12 11h4M12 16h4M8 11h.01M8 16h.01" />
    </svg>
  );
}

function ScheduleIcon({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none">
      <rect x="3.5" y="5" width="17" height="15.5" rx="2" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M7.5 3v4M16.5 3v4M3.5 10h17M8 14h3m2 0h3m-8 3h3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

const primaryNavigation = [
  { to: "/", label: "Головна", Icon: HomeIcon, end: true },
  { to: "/programs", label: "Програми", Icon: ProgramsIcon, end: false },
  { to: "/schedule", label: "Розклад", Icon: ScheduleIcon, end: false },
];
const progressNavigation = [
  { to: "/progress", label: "Огляд прогресу", Icon: ProgressIcon, end: true },
  { to: "/stats", label: "Статистика", Icon: StatsIcon, end: false },
  { to: "/history", label: "Історія", Icon: HistoryIcon, end: false },
  { to: "/points", label: "Бали", Icon: PointsIcon, end: false },
  { to: "/achievements", label: "Досягнення", Icon: AchievementIcon, end: false },
  { to: "/challenges", label: "Челенджі", Icon: ChallengeIcon, end: false },
  { to: "/leaderboard", label: "Рейтинг", Icon: LeaderboardIcon, end: false },
];
const moreNavigation = [
  { to: "/profile", label: "Профіль", Icon: ProfileIcon, end: false },
  { to: "/catalog", label: "Каталог", Icon: CatalogIcon, end: false },
  { to: "/settings", label: "Налаштування", Icon: SettingsIcon, end: false },
];
const progressPaths = [
  "/progress",
  "/stats",
  "/history",
  "/points",
  "/achievements",
  "/challenges",
  "/leaderboard",
  "/completed",
];
const morePaths = ["/more", "/profile", "/catalog", "/settings", "/notifications"];
const mobileNavigation = [
  { to: "/", label: "Головна", Icon: HomeIcon, end: true },
  { to: "/schedule", label: "Розклад", Icon: ScheduleIcon, end: false },
  { to: "/programs", label: "Програми", Icon: ProgramsIcon, end: false },
  { to: "/progress", label: "Прогрес", Icon: ProgressIcon, end: true, paths: progressPaths },
  { to: "/more", label: "Ще", Icon: MoreIcon, end: true, paths: morePaths },
];

export function AuthenticatedLayout({ account, onLogout, logoutBusy = false }: AuthenticatedLayoutProps): JSX.Element {
  const unreadNotifications = useUnreadNotificationCount();
  const { pathname } = useLocation();
  const renderLinks = (items: typeof primaryNavigation) =>
    items.map(({ to, label, Icon, end }) => (
      <NavLink
        key={to}
        to={to}
        end={end}
        className={({ isActive }) =>
          `flex min-h-11 min-w-0 items-center gap-space-3 rounded-field px-space-3 py-space-2 text-small font-semibold no-underline transition-colors duration-150 hover:bg-interactive-hover-state hover:text-foreground motion-reduce:transition-none ${isActive ? "bg-selected-state text-brand" : "text-muted-foreground"}`
        }
      >
        <Icon className="size-5 shrink-0" />
        <span>{label}</span>
      </NavLink>
    ));
  return (
    <div className="flex min-h-svh bg-background">
      <a
        className="fixed left-space-2 top-space-2 z-50 -translate-y-[calc(100%_+_var(--space-4))] rounded-field bg-primary px-space-4 py-space-2 text-primary-foreground focus-visible:translate-y-0"
        href="#main-content"
      >
        Пропустити до вмісту
      </a>
      <aside
        className="sticky top-0 hidden h-svh w-[var(--layout-sidebar-width)] shrink-0 flex-col gap-space-6 overflow-y-auto border-r border-outline bg-card px-space-4 py-space-6 lg:flex"
        aria-label="Бічна панель"
      >
        <Link
          className="inline-flex w-fit items-center gap-space-3 px-space-2 text-foreground no-underline"
          to="/"
          aria-label="Фітнес-трекер — головна"
        >
          <span className="grid size-11 shrink-0 place-items-center rounded-md bg-brand text-primary-foreground">
            <FitnessMark className="size-6" />
          </span>
          <span className="grid gap-0.5">
            <span className="text-title-medium font-bold leading-[var(--line-height-title-medium)]">Фітнес-трекер</span>
            <span className="text-caption font-medium text-muted-foreground">Nordic Vitality</span>
          </span>
        </Link>

        <nav className="grid gap-space-1" aria-label="Розділи застосунку">
          <p className="m-0 px-space-3 pt-space-1 text-caption font-semibold uppercase text-muted-foreground">
            Основне
          </p>
          {renderLinks(primaryNavigation)}
          <p className="m-0 px-space-3 pt-space-3 text-caption font-semibold uppercase text-muted-foreground">
            Прогрес
          </p>
          {renderLinks(progressNavigation)}
          <p className="m-0 px-space-3 pt-space-3 text-caption font-semibold uppercase text-muted-foreground">Інше</p>
          {renderLinks(moreNavigation)}
          <NotificationNavLink count={unreadNotifications} variant="sidebar" />
        </nav>
        <p className="mt-auto mb-0 p-space-3 text-caption text-muted-foreground">Твій ритм. Твій прогрес.</p>
      </aside>

      <div className="flex min-h-svh min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex min-h-[var(--layout-header-height)] items-center justify-between gap-space-4 border-b border-outline bg-card px-space-4 sm:px-space-8">
          <Link
            className="inline-flex items-center gap-space-3 text-foreground no-underline lg:hidden"
            to="/"
            aria-label="Фітнес-трекер — головна"
          >
            <span className="grid size-9 shrink-0 place-items-center rounded-field bg-brand text-primary-foreground">
              <FitnessMark className="size-5" />
            </span>
            <span className="max-w-[9rem] truncate text-small font-bold max-[480px]:max-w-[6.25rem]">
              Фітнес-трекер
            </span>
          </Link>
          <div className="ml-auto flex min-w-0 items-center gap-space-4 max-[480px]:gap-space-2">
            <NotificationNavLink count={unreadNotifications} variant="header" />
            <span
              className="max-w-[min(40vw,28rem)] truncate text-small text-muted-foreground max-[480px]:hidden"
              title={account.email}
            >
              {account.email}
            </span>
            <Button variant="outlined" size="sm" onClick={onLogout} loading={logoutBusy}>
              Вийти
            </Button>
          </div>
        </header>

        <main
          className="w-full flex-1 pb-[calc(var(--layout-mobile-nav-height)+env(safe-area-inset-bottom,0px)+var(--space-4))] outline-none lg:pb-0"
          id="main-content"
          tabIndex={-1}
        >
          <div className="mx-auto w-full max-w-[var(--layout-content-max-width)] px-space-4 py-space-6 sm:px-space-8 sm:py-space-8">
            <Outlet />
          </div>
        </main>

        <nav
          className="fixed inset-x-0 bottom-0 z-30 grid min-h-[var(--layout-mobile-nav-height)] grid-cols-5 border-t border-outline bg-card pb-[env(safe-area-inset-bottom,0px)] lg:hidden"
          aria-label="Мобільна навігація"
        >
          {mobileNavigation.map(({ to, label, Icon, end, paths }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              aria-label={label}
              className={({ isActive }) =>
                `flex min-w-0 flex-col items-center justify-center gap-0.5 p-space-1 text-caption no-underline transition-colors duration-150 hover:bg-interactive-hover-state hover:text-foreground motion-reduce:transition-none ${isActive || paths?.some((path) => pathname === path || pathname.startsWith(`${path}/`)) ? "bg-selected-state text-brand" : "text-muted-foreground"}`
              }
            >
              <Icon className="size-5 shrink-0" />
              <span className="w-full truncate text-center text-[0.6875rem] leading-tight">{label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
