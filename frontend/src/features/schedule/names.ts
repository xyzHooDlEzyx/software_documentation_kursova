import { getWorkout } from "@/features/catalog/api";
import { getProgram, type UserProgramDetail } from "@/features/programs/api";
import type { ScheduledSession } from "./api";

const workoutCache = new Map<number, Promise<string>>();
const programCache = new Map<number, Promise<UserProgramDetail | null>>();

function workoutName(id: number) {
  let pending = workoutCache.get(id);
  if (!pending) {
    pending = getWorkout(id).then(
      (item) => item.name,
      () => { workoutCache.delete(id); return `Тренування #${id}`; },
    );
    workoutCache.set(id, pending);
  }
  return pending;
}

function program(id: number) {
  let pending = programCache.get(id);
  if (!pending) {
    pending = getProgram(id).then(
      (item) => item,
      () => { programCache.delete(id); return null; },
    );
    programCache.set(id, pending);
  }
  return pending;
}

export type SessionNames = { workout: string; program: string | null };

export async function resolveSessionNames(items: ScheduledSession[]) {
  const result = new Map<number, SessionNames>();
  await Promise.all(items.map(async (item) => {
    const programData = item.user_program_id ? await program(item.user_program_id) : null;
    const programWorkout = programData?.workouts.find((workout) => workout.entry_id === item.user_program_workout_id);
    result.set(item.id, {
      workout: programWorkout?.name ?? await workoutName(item.source_workout_id),
      program: programData?.name ?? (item.user_program_id ? `Програма #${item.user_program_id}` : null),
    });
  }));
  return result;
}

export function clearSessionNameCache() {
  workoutCache.clear();
  programCache.clear();
}
