import { listExercises, type Exercise } from "./api";

/** Loads every visible exercise (optionally of one category) across pages. */
export async function fetchAllExercises(category?: string): Promise<Exercise[]> {
  const all: Exercise[] = [];
  for (let page = 1; ; page += 1) {
    const chunk = await listExercises({ category, page, pageSize: 100 });
    all.push(...chunk.results);
    if (!chunk.next) return all;
  }
}

export function exerciseNames(exercises: Exercise[]) {
  return new Map(exercises.map((exercise) => [exercise.id, exercise.name]));
}
