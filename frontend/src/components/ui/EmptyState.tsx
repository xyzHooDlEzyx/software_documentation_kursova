import type { ReactNode } from "react";

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="grid justify-items-center gap-space-2 rounded-panel border border-dashed border-input-border bg-card px-space-6 py-space-10 text-center">
      <p className="m-0 text-title-small font-semibold text-foreground">{title}</p>
      {children && <div className="max-w-[36rem] text-small text-muted-foreground">{children}</div>}
    </div>
  );
}
