import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  hint?: string;
  error?: string;
}

export function TextInput({ id, label, hint, error, className = "", ...props }: TextInputProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [props["aria-describedby"], hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className="grid gap-space-1">
      <label className="text-sm font-semibold text-foreground" htmlFor={id}>{label}</label>
      <input
        {...props}
        id={id}
        className={cn("h-11 w-full rounded-field border bg-card px-3 text-base text-foreground shadow-xs outline-none transition-colors placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50", error ? "border-status-error" : "border-input-border focus-visible:border-secondary", className)}
        aria-invalid={error ? true : props["aria-invalid"]}
        aria-describedby={describedBy}
      />
      {hint && <span className="text-xs text-muted-foreground" id={hintId}>{hint}</span>}
      {error && <span className="text-xs text-status-error" id={errorId}>{error}</span>}
    </div>
  );
}
