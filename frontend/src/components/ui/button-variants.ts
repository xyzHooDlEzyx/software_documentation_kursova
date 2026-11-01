import { cva } from "class-variance-authority";

export type ButtonVariant = "primary" | "secondary" | "outlined" | "inverted" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

export const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-field font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-brand",
        secondary: "bg-secondary text-secondary-foreground hover:bg-brand-secondary-token",
        outlined: "border border-input-border bg-card text-foreground hover:bg-interactive-hover-state",
        inverted: "bg-card text-primary hover:bg-selected-state",
        danger: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-11 px-4 text-sm",
        lg: "h-13 px-5 text-base",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);
