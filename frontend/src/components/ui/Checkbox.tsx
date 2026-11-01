import { useRef, type ChangeEvent, type ChangeEventHandler, type ComponentProps, type InputHTMLAttributes } from "react";
import { Checkbox as BaseCheckbox } from "@base-ui/react/checkbox";

import { cn } from "@/lib/utils";

type CheckboxRootProps = ComponentProps<typeof BaseCheckbox.Root>;

export interface CheckboxProps extends Omit<CheckboxRootProps, "id" | "checked" | "defaultChecked" | "disabled" | "required" | "readOnly" | "name" | "value" | "form" | "inputRef" | "onCheckedChange" | "className"> {
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

export function Checkbox({ id, label, error, className = "", checked, defaultChecked, disabled, required, readOnly, name, value, form, onChange, ...props }: CheckboxProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const errorId = error ? `${id}-error` : undefined;
  const labelId = `${id}-label`;
  const describedBy = [props["aria-describedby"], errorId].filter(Boolean).join(" ") || undefined;

  function handleCheckedChange() {
    if (!onChange) return;
    const target = inputRef.current ?? ({ checked: Boolean(checked) } as HTMLInputElement);
    onChange({ target, currentTarget: target } as ChangeEvent<HTMLInputElement>);
  }

  return (
    <div className="grid gap-space-1">
      <label className="inline-flex cursor-pointer items-center gap-space-2 text-sm text-foreground" htmlFor={id}>
        <BaseCheckbox.Root
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
          aria-invalid={error ? true : props["aria-invalid"]}
          aria-describedby={describedBy}
          aria-labelledby={labelId}
          onCheckedChange={handleCheckedChange}
          className={cn("peer inline-flex size-4 shrink-0 items-center justify-center rounded-sm border border-input-border bg-card text-secondary-foreground outline-none transition-colors data-[checked]:border-secondary data-[checked]:bg-secondary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-status-error", className)}
        >
          <BaseCheckbox.Indicator className="inline-flex items-center justify-center">
            <svg className="size-3" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="m3.5 8 3 3 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </BaseCheckbox.Indicator>
        </BaseCheckbox.Root>
        <span id={labelId}>{label}</span>
      </label>
      {error && <span className="text-xs text-status-error" id={errorId}>{error}</span>}
    </div>
  );
}
