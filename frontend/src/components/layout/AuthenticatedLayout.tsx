import type { JSX } from "react";
import { Link, NavLink, Outlet } from "react-router";

import type { Account } from "../../app/api";
import { Button } from "../ui";
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
  return <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none"><path d="m3.5 10 8.5-7 8.5 7v10.5h-6v-6h-5v6h-6V10Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" /></svg>;
}

function SettingsIcon({ className = "" }: { className?: string }) {
  return <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none"><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z" stroke="currentColor" strokeWidth="1.8" /><path d="m19.4 15 .1.1a1.8 1.8 0 1 1-2.5 2.5l-.1-.1a1.8 1.8 0 0 0-3 .9v.2a1.8 1.8 0 1 1-3.6 0v-.2a1.8 1.8 0 0 0-3-.9l-.1.1a1.8 1.8 0 1 1-2.5-2.5l.1-.1a1.8 1.8 0 0 0-.9-3H3.7a1.8 1.8 0 1 1 0-3.6h.2a1.8 1.8 0 0 0 .9-3l-.1-.1a1.8 1.8 0 1 1 2.5-2.5l.1.1a1.8 1.8 0 0 0 3-.9v-.2a1.8 1.8 0 1 1 3.6 0v.2a1.8 1.8 0 0 0 3 .9l.1-.1a1.8 1.8 0 1 1 2.5 2.5l.1.1a1.8 1.8 0 0 0 .9 3h.2a1.8 1.8 0 1 1 0 3.6h-.2a1.8 1.8 0 0 0-.9 3Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" /></svg>;
}

const navigation = [
  { to: "/", label: "Головна", Icon: HomeIcon, end: true },
  { to: "/settings", label: "Налаштування", Icon: SettingsIcon, end: false },
];

export function AuthenticatedLayout({
  account,
  onLogout,
  logoutBusy = false,
}: AuthenticatedLayoutProps): JSX.Element {
  return (
    <div className="flex min-h-svh bg-background">
      <a className="fixed left-space-2 top-space-2 z-50 -translate-y-[calc(100%_+_var(--space-4))] rounded-field bg-primary px-space-4 py-space-2 text-primary-foreground focus-visible:translate-y-0" href="#main-content">Пропустити до вмісту</a>
      <aside className="sticky top-0 hidden h-svh w-[var(--layout-sidebar-width)] shrink-0 flex-col gap-space-8 border-r border-outline bg-card px-space-4 py-space-6 lg:flex" aria-label="Основна навігація">
        <Link className="inline-flex w-fit items-center gap-space-3 px-space-2 text-foreground no-underline" to="/" aria-label="Фітнес-трекер — головна">
          <span className="grid size-11 shrink-0 place-items-center rounded-md bg-brand text-primary-foreground">
            <FitnessMark className="size-6" />
          </span>
          <span className="grid gap-0.5">
            <span className="text-title-medium font-bold leading-[var(--line-height-title-medium)]">Фітнес-трекер</span>
            <span className="text-caption font-medium text-muted-foreground">Nordic Vitality</span>
          </span>
        </Link>

        <nav className="grid gap-space-1" aria-label="Розділи застосунку">
          {navigation.map(({ to, label, Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `flex min-h-11 min-w-0 items-center gap-space-3 rounded-field px-space-3 py-space-2 text-small font-semibold no-underline transition-colors duration-150 hover:bg-interactive-hover-state hover:text-foreground motion-reduce:transition-none ${isActive ? "bg-selected-state text-brand" : "text-muted-foreground"}`}
            >
              <Icon className="size-5 shrink-0" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <p className="mt-auto mb-0 p-space-3 text-caption text-muted-foreground">Твій ритм. Твій прогрес.</p>
      </aside>

      <div className="flex min-h-svh min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex min-h-[var(--layout-header-height)] items-center justify-between gap-space-4 border-b border-outline bg-card px-space-4 sm:px-space-8">
          <Link className="inline-flex items-center gap-space-3 text-foreground no-underline lg:hidden" to="/" aria-label="Фітнес-трекер — головна">
            <span className="grid size-9 shrink-0 place-items-center rounded-field bg-brand text-primary-foreground">
              <FitnessMark className="size-5" />
            </span>
            <span className="max-w-[9rem] truncate text-small font-bold max-[480px]:max-w-[6.25rem]">Фітнес-трекер</span>
          </Link>
          <div className="ml-auto flex min-w-0 items-center gap-space-4 max-[480px]:gap-space-2">
            <span className="max-w-[min(40vw,28rem)] truncate text-small text-muted-foreground max-[480px]:max-w-28 max-[480px]:text-caption" title={account.email}>{account.email}</span>
            <Button variant="outlined" size="sm" onClick={onLogout} loading={logoutBusy}>
              Вийти
            </Button>
          </div>
        </header>

        <main className="w-full flex-1 pb-[calc(var(--layout-mobile-nav-height)+env(safe-area-inset-bottom,0px)+var(--space-4))] outline-none lg:pb-0" id="main-content" tabIndex={-1}>
          <div className="mx-auto w-full max-w-[var(--layout-content-max-width)] px-space-4 py-space-6 sm:px-space-8 sm:py-space-8"><Outlet /></div>
        </main>

        <nav className="fixed inset-x-0 bottom-0 z-30 grid min-h-[var(--layout-mobile-nav-height)] grid-cols-2 border-t border-outline bg-card pb-[env(safe-area-inset-bottom,0px)] lg:hidden" aria-label="Основна навігація">
          {navigation.map(({ to, label, Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `flex min-w-0 flex-col items-center justify-center gap-0.5 p-space-1 text-caption no-underline transition-colors duration-150 hover:bg-interactive-hover-state hover:text-foreground motion-reduce:transition-none ${isActive ? "bg-selected-state text-brand" : "text-muted-foreground"}`}
            >
              <Icon className="size-5 shrink-0" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
