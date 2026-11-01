import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export interface LoadingStateProps extends HTMLAttributes<HTMLDivElement> {
  text: string;
}

export function LoadingState({ text, className = "", ...props }: LoadingStateProps) {
  return <div {...props} className={cn("inline-flex items-center gap-space-2 text-sm text-muted-foreground", className)} role="status"><svg className="size-4 animate-spin" aria-hidden="true" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z" /></svg>{text}</div>;
}
