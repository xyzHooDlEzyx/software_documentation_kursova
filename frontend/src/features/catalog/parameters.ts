import { formatDecimal } from "@/lib/format";
import type { RecommendedParameters } from "./api";

/** Human summary of category-specific recommended parameters (BR-002/BR-004). */
export function describeParameters(item: RecommendedParameters) {
  const parts: string[] = [];
  if (item.recommended_sets !== null && item.recommended_reps !== null) parts.push(`${item.recommended_sets} × ${item.recommended_reps}`);
  if (item.recommended_load_kg !== null && Number(item.recommended_load_kg) > 0) parts.push(formatDecimal(item.recommended_load_kg, "кг"));
  if (item.recommended_duration_min !== null) parts.push(formatDecimal(item.recommended_duration_min, "хв"));
  if (item.recommended_distance_km !== null) parts.push(formatDecimal(item.recommended_distance_km, "км"));
  return parts.join(" · ") || "—";
}
