import { useSearchParams } from "react-router";
import { periodFor, validPeriod, type DatePeriod, type PeriodPreset } from "./period";

export function usePeriod(defaultPreset: Exclude<PeriodPreset, "custom"> = "month") {
  const [params, setParams] = useSearchParams();
  const requested = params.get("period") as PeriodPreset | null;
  const preset: PeriodPreset =
    requested && ["week", "month", "three-months", "custom"].includes(requested) ? requested : defaultPreset;
  const fallback = periodFor(defaultPreset);
  const candidate: DatePeriod = {
    startDate: params.get("start_date") ?? fallback.startDate,
    endDate: params.get("end_date") ?? fallback.endDate,
  };
  const period =
    preset === "custom" && validPeriod(candidate) ? candidate : preset === "custom" ? fallback : periodFor(preset);
  function change(nextPreset: PeriodPreset, next: DatePeriod) {
    const query = new URLSearchParams(params);
    query.set("period", nextPreset);
    query.set("start_date", next.startDate);
    query.set("end_date", next.endDate);
    query.delete("page");
    setParams(query);
  }
  return { preset, period, change };
}
