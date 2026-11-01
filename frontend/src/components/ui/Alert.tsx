import type { HTMLAttributes, ReactNode } from "react";
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils";

export type AlertTone = "info" | "success" | "warning" | "error";
export interface AlertProps extends Omit<HTMLAttributes<HTMLDivElement>, "children"> {
  tone?: AlertTone;
  children: ReactNode;
}

const alertVariants = cva("rounded-field border px-space-4 py-space-3 text-base", {
  variants: {
    tone: {
      info: "border-ring/30 bg-muted text-foreground",
      success: "border-status-success/30 bg-status-success/10 text-foreground",
      warning: "border-status-warning/30 bg-status-warning/10 text-foreground",
      error: "border-status-error/30 bg-status-error/10 text-foreground",
    },
  },
  defaultVariants: { tone: "info" },
});

export function Alert({ tone = "info", children, className = "", role, ...props }: AlertProps) {
  const liveRole = role ?? (tone === "error" || tone === "warning" ? "alert" : "status");
  return <div {...props} className={cn(alertVariants({ tone }), className)} role={liveRole} aria-live={liveRole === "alert" ? "assertive" : "polite"}>{children}</div>;
}
