import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export type CardProps = HTMLAttributes<HTMLDivElement>;

export function Card({ className = "", ...props }: CardProps) {
  return <div {...props} className={cn("rounded-panel border border-input-border bg-card p-space-5 text-card-foreground shadow-panel", className)} />;
}
