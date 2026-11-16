import { Select, TextInput } from "@/components/ui";
import { periodFor, type DatePeriod, type PeriodPreset } from "./period";

export function PeriodPicker({
  preset,
  period,
  onChange,
}: {
  preset: PeriodPreset;
  period: DatePeriod;
  onChange: (preset: PeriodPreset, period: DatePeriod) => void;
}) {
  return (
    <div className="grid gap-space-3 sm:grid-cols-3" aria-label="Період">
      <Select
        id="period-preset"
        label="Період"
        value={preset}
        options={[
          { value: "week", label: "Цей тиждень" },
          { value: "month", label: "Цей місяць" },
          { value: "three-months", label: "Останні 3 місяці" },
          { value: "custom", label: "Власний період" },
        ]}
        onChange={(event) => {
          const next = event.target.value as PeriodPreset;
          onChange(next, next === "custom" ? period : periodFor(next));
        }}
      />
      {preset === "custom" && (
        <>
          <TextInput
            id="period-start"
            label="Від"
            type="date"
            value={period.startDate}
            onChange={(event) => onChange(preset, { ...period, startDate: event.target.value })}
          />
          <TextInput
            id="period-end"
            label="До (не включно)"
            type="date"
            value={period.endDate}
            onChange={(event) => onChange(preset, { ...period, endDate: event.target.value })}
          />
        </>
      )}
    </div>
  );
}
