import type { JSX } from "react";
import { Link, Outlet } from "react-router";

import { Card } from "../ui";
import "./layout.css";

function FitnessMark({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none">
      <path d="M6.5 8v8M4 10v4m13.5-6v8M20 10v4M8 12h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function PublicLayout(): JSX.Element {
  return (
    <main className="mx-auto grid min-h-svh w-full max-w-[90rem] grid-cols-1 grid-rows-[auto_1fr] overflow-hidden bg-card shadow-panel md:grid-cols-[5fr_7fr] md:grid-rows-1">
      <section className="relative isolate flex min-h-[12.5rem] min-w-0 overflow-hidden bg-brand px-space-4 py-space-4 text-primary-foreground sm:px-space-8 sm:py-space-8 md:min-h-svh md:px-[clamp(2rem,5vw,3.5rem)] md:py-[clamp(2rem,5vw,3.5rem)]" aria-labelledby="public-brand-title">
        <div className="z-10 flex w-full flex-col justify-start gap-space-4 md:justify-between md:gap-space-8">
          <Link className="inline-flex w-fit items-center gap-space-3 text-inherit no-underline" to="/" aria-label="Фітнес-трекер">
            <span className="grid size-9 shrink-0 place-items-center rounded-md bg-brand-accent-token text-brand sm:size-11">
              <FitnessMark className="size-5 sm:size-6" />
            </span>
            <span className="grid gap-0.5">
              <span className="text-small font-bold sm:text-title-medium sm:leading-[var(--line-height-title-medium)]">Фітнес-трекер</span>
              <span className="text-caption font-medium text-brand-accent-token">Особистий кабінет</span>
            </span>
          </Link>

          <div className="max-w-[32rem] py-0 md:py-space-12">
            <p className="mb-space-2 hidden text-caption font-bold uppercase tracking-[0.08em] text-brand-accent-token md:block">Nordic Vitality</p>
            <h1 className="mb-space-1 max-w-none text-title-large font-extrabold leading-[var(--line-height-title-large)] tracking-[var(--letter-spacing-heading)] sm:mb-space-4 md:max-w-[12ch] md:text-display md:leading-[1.1]" id="public-brand-title">Рухайся до своєї мети</h1>
            <p className="m-0 max-w-[36rem] text-small text-selected-state sm:text-body-large sm:leading-[var(--line-height-body-large)]">Плануй заняття та відстежуй власний прогрес у зручному особистому кабінеті.</p>
          </div>
          <p className="m-0 hidden text-small text-selected-state md:block">Твій ритм. Твій прогрес.</p>
        </div>
        <span className="layout-glow pointer-events-none absolute -z-0 right-[-10rem] top-[-12rem] aspect-square w-[22rem] rounded-full border border-brand-accent-token/10" aria-hidden="true" />
        <span className="layout-glow pointer-events-none absolute -z-0 bottom-[-17rem] left-[-12rem] aspect-square w-[28rem] rounded-full border border-brand-accent-token/10" aria-hidden="true" />
      </section>

      <section className="grid min-w-0 flex-1 content-start justify-items-center bg-card px-space-4 py-space-6 sm:px-space-8 sm:py-[clamp(1.5rem,5vw,4.5rem)] lg:content-center" aria-label="Вхід або створення облікового запису">
        <Card className="w-full max-w-[28rem] border-0 p-0 shadow-none md:max-w-[32rem]">
          <Outlet />
        </Card>
      </section>
    </main>
  );
}
