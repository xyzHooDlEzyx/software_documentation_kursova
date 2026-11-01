import { useRef, type ChangeEvent, type ChangeEventHandler, type ComponentProps, type InputHTMLAttributes } from "react";
import { Switch as BaseSwitch } from "@base-ui/react/switch";

import { cn } from "@/lib/utils";

type SwitchRootProps = ComponentProps<typeof BaseSwitch.Root>;

export interface SwitchProps extends Omit<SwitchRootProps, "id" | "checked" | "defaultChecked" | "disabled" | "required" | "readOnly" | "name" | "value" | "form" | "inputRef" | "onCheckedChange" | "className"> {
  id: string;
  label: string;
  error?: string;
  checked?: boolean;
  defaultChecked?: boolean;
  disabled?: boolean;
  required?: boolean;
  readOnly?: boolean;
  name?: string;
  value?: InputHTMLAttributes<HTMLInputElement>["value"];
  form?: string;
  className?: string;
  onChange?: ChangeEventHandler<HTMLInputElement>;
}

export function Switch({ id, label, error, className = "", checked, defaultChecked, disabled, required, readOnly, name, value, form, onChange, ...props }: SwitchProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [props["aria-describedby"], errorId].filter(Boolean).join(" ") || undefined;
  const labelId = `${id}-label`;

  function handleCheckedChange(nextChecked: boolean) {
    if (!onChange) return;
    const target = inputRef.current ?? ({ checked: nextChecked } as HTMLInputElement);
    const event = { target, currentTarget: target } as ChangeEvent<HTMLInputElement>;
    onChange(event);
  }

  return (
    <div className="grid gap-space-1">
      <div className="inline-flex items-center gap-space-3 text-sm text-foreground">
        <span id={labelId}>{label}</span>
        <BaseSwitch.Root
          {...props}
          id={id}
          checked={checked}
          defaultChecked={defaultChecked}
          disabled={disabled}
          required={required}
          readOnly={readOnly}
          name={name}
          value={value === undefined ? undefined : String(value)}
          form={form}
          inputRef={inputRef}
          aria-labelledby={labelId}
          aria-describedby={describedBy}
          aria-invalid={error ? true : props["aria-invalid"]}
          onCheckedChange={handleCheckedChange}
          className={cn("inline-flex h-6 w-10 shrink-0 cursor-pointer items-center rounded-full border border-transparent bg-muted transition-colors data-[checked]:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-status-error", className)}
        >
          <BaseSwitch.Thumb className="pointer-events-none block size-4 translate-x-0 rounded-full bg-card shadow-sm transition-transform data-[checked]:translate-x-4" />
        </BaseSwitch.Root>
      </div>
      {error && <span className="text-xs text-status-error" id={errorId}>{error}</span>}
    </div>
  );
}
