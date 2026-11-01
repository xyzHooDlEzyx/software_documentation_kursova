import type { ReactNode } from "react";
import type { JSX } from "react";

import "./layout.css";

export type PageHeaderProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  children?: ReactNode;
};

export function PageHeader({ title, eyebrow, description, children }: PageHeaderProps): JSX.Element {
  return (
    <header className="mb-space-6 flex items-end justify-between gap-space-6 max-[480px]:items-start max-[480px]:flex-col max-[480px]:gap-space-3">
      <div className="min-w-0">
        {eyebrow && <p className="mb-space-2 text-caption font-bold uppercase tracking-[0.08em] text-muted-foreground">{eyebrow}</p>}
        <h1 className="m-0 text-page-title font-bold leading-[var(--line-height-page-title)] tracking-[var(--letter-spacing-heading)] text-foreground max-[480px]:text-[length:var(--font-size-page-title-mobile)] max-[480px]:leading-[var(--line-height-page-title-mobile)]">{title}</h1>
        {description && <p className="mt-space-2 mb-0 max-w-[48rem] text-body leading-body text-muted-foreground">{description}</p>}
      </div>
      {children && <div className="flex shrink-0 flex-wrap items-center gap-space-2">{children}</div>}
    </header>
  );
}
