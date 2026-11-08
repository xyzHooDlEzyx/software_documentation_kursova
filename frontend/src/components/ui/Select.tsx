import type { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  id: string;
  label: string;
  options: { value: string; label: string }[];
  placeholder?: string;
  hint?: string;
  error?: string;
}

export function Select({ id, label, options, placeholder, hint, error, className = "", ...props }: SelectProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className="grid content-start gap-space-1">
      <label className="text-sm font-semibold text-foreground" htmlFor={id}>{label}</label>
      <select
        {...props}
        id={id}
        className={cn("h-11 w-full rounded-field border bg-card px-3 text-base text-foreground shadow-xs outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50", error ? "border-status-error" : "border-input-border", className)}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
      {hint && <span className="text-xs text-muted-foreground" id={hintId}>{hint}</span>}
      {error && <span className="text-xs text-status-error" id={errorId}>{error}</span>}
    </div>
  );
}
