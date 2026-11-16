import type { HTMLAttributes } from "react";
import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded-chip px-space-2 py-0.5 text-caption font-semibold", {
  variants: {
    tone: {
      neutral: "bg-muted text-foreground",
      brand: "bg-brand text-primary-foreground",
      accent: "bg-accent text-accent-foreground",
      success: "bg-muted text-foreground ring-1 ring-status-success",
      outline: "border border-input-border text-muted-foreground",
    },
  },
  defaultVariants: { tone: "neutral" },
});

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: "neutral" | "brand" | "accent" | "outline" | "success";
}

export function Badge({ tone, className = "", ...props }: BadgeProps) {
  return <span {...props} className={cn(badgeVariants({ tone }), className)} />;
}
