import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Button as BaseButton } from "@base-ui/react/button";

import { cn } from "@/lib/utils";
import { buttonVariants, type ButtonSize, type ButtonVariant } from "./button-variants";

export type { ButtonSize, ButtonVariant } from "./button-variants";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  startIcon?: ReactNode;
  endIcon?: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  startIcon,
  endIcon,
  disabled,
  children,
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <BaseButton {...props} className={cn(buttonVariants({ variant, size }), className)} type={type} disabled={disabled || loading} aria-busy={loading || undefined}>
      {loading ? <svg className="size-4 animate-spin" aria-hidden="true" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z" /></svg> : startIcon && <span className="inline-flex items-center" aria-hidden="true">{startIcon}</span>}
      <span>{loading ? "Зачекайте…" : children}</span>
      {!loading && endIcon && <span className="inline-flex items-center" aria-hidden="true">{endIcon}</span>}
    </BaseButton>
  );
}
