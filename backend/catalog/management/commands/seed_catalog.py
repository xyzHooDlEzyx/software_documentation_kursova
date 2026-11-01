"""Management command to idempotently seed the shared fitness catalog.

Seeds:
- 10 exercises (strength, cardio, yoga, verified C2024 codes and 1 null-MET)
- 6 workouts (with valid compositions and parameters per BR-002)
- 6 published program templates (3 paired sets for Phase 4 strategies per BR-003)
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import ExperienceLevel, FitnessGoal
from catalog.models import (
    Exercise,
    ExerciseCategory,
    ProgramTemplate,
    ProgramTemplateStatus,
    ProgramTemplateWorkout,
    Workout,
    WorkoutExercise,
)
from catalog.services import CatalogPublicationService


class Command(BaseCommand):
    help = "Seed shared catalog with exercises, workouts, and published templates."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Starting shared catalog seeding...")

        # 1. Seed 10 Exercises
        exercises_specs = [
            # Strength exercises
            {
                "name": "Присідання зі штангою",
                "category": ExerciseCategory.STRENGTH,
                "description": (
                    "Базова багатосуглобова вправа для м'язів ніг та сідниць."
                ),
                "met_value": Decimal("5.00"),
                "met_activity_code": "02052",
                "met_reference_version": "Compendium 2024",
                "met_activity_description": (
                    "resistance training, squats, vigorous effort"
                ),
            },
            {
                "name": "Жим лежачи",
                "category": ExerciseCategory.STRENGTH,
                "description": (
                    "Класичний жим штанги на горизонтальній лаві для грудей."
                ),
                "met_value": Decimal("6.00"),
                "met_activity_code": "02054",
                "met_reference_version": "Compendium 2024",
                "met_activity_description": (
                    "resistance training, power lifting, vigorous effort"
                ),
            },
            {
                "name": "Станова тяга",
                "category": ExerciseCategory.STRENGTH,
                "description": (
                    "Фундаментальна вправа для розвитку заднього ланцюга м'язів."
                ),
                "met_value": Decimal("6.00"),
                "met_activity_code": "02054",
                "met_reference_version": "Compendium 2024",
                "met_activity_description": (
                    "resistance training, power lifting, vigorous effort"
                ),
            },
            {
                "name": "Підтягування",
                "category": ExerciseCategory.STRENGTH,
                "description": (
                    "Вправа з власною вагою на перекладині для м'язів спини."
                ),
                "met_value": Decimal("8.00"),
                "met_activity_code": "02022",
                "met_reference_version": "Compendium 2024",
                "met_activity_description": "calisthenics, vigorous effort",
            },
            # Cardio exercises
            {
                "name": "Біг на біговій доріжці",
                "category": ExerciseCategory.CARDIO,
                "description": (
                    "Рівномірний біг середньої інтенсивності для витривалості."
                ),
                "met_value": Decimal("9.80"),
                "met_activity_code": "12020",
                "met_reference_version": "Compendium 2024",
                "met_activity_description": "running, 6 mph (10 min/mile)",
            },
            {
                "name": "Велотренажер",
                "category": ExerciseCategory.CARDIO,
                "description": "Аеробне педалювання на стаціонарному велотренажері.",
                "met_value": Decimal("6.80"),
                "met_activity_code": "01200",
                "met_reference_version": "Compendium 2024",
                "met_activity_description": (
                    "bicycling, stationary, moderate to vigorous effort"
                ),
            },
            {
                "name": "Стрибки на скакалці",
                "category": ExerciseCategory.CARDIO,
                "description": (
                    "Високоінтенсивні кардіо-стрибки для координації та витривалості."
                ),
                "met_value": Decimal("12.30"),
                "met_activity_code": "02024",
                "met_reference_version": "Compendium 2024",
                "met_activity_description": "rope jumping, moderate pace",
            },
            # Yoga exercises
            {
                "name": "Хатха-йога",
                "category": ExerciseCategory.YOGA,
                "description": (
                    "Класичні асани на баланс, статику та дихальні практики."
                ),
                "met_value": Decimal("2.50"),
                "met_activity_code": "02150",
                "met_reference_version": "Compendium 2024",
                "met_activity_description": "yoga, Hatha",
            },
            {
                "name": "Віньяса-йога",
                "category": ExerciseCategory.YOGA,
                "description": "Динамічний потік асан, синхронізованих з диханням.",
                "met_value": Decimal("4.00"),
                "met_activity_code": "02180",
                "met_reference_version": "Compendium 2024",
                "met_activity_description": "yoga, Power or Vinyasa",
            },
            # Exercise without MET metadata (valid per model rules)
            {
                "name": "Розминка та стретчинг",
                "category": ExerciseCategory.YOGA,
                "description": (
                    "Суглобова гімнастика та загальна розтяжка всього тіла."
                ),
                "met_value": None,
                "met_activity_code": None,
                "met_reference_version": None,
                "met_activity_description": None,
            },
        ]

        exercise_map = {}
        for spec in exercises_specs:
            exercise, created = Exercise.objects.get_or_create(
                name=spec["name"],
                defaults=spec,
            )
            if not created:
                for k, v in spec.items():
                    setattr(exercise, k, v)
                exercise.is_archived = False
                exercise.full_clean()
                exercise.save()
            exercise_map[spec["name"]] = exercise

        self.stdout.write(f"Seeded {len(exercise_map)} exercises.")

        # 2. Seed 6 Workouts with valid compositions
        workouts_specs = [
            {
                "name": "Силове тренування А",
                "category": ExerciseCategory.STRENGTH,
                "description": "Базовий спліт А: присідання, жим та підтягування.",
                "exercises": [
                    {
                        "exercise": exercise_map["Присідання зі штангою"],
                        "position": 1,
                        "recommended_sets": 4,
                        "recommended_reps": 8,
                        "recommended_load_kg": Decimal("70.0"),
                    },
                    {
                        "exercise": exercise_map["Жим лежачи"],
                        "position": 2,
                        "recommended_sets": 4,
                        "recommended_reps": 8,
                        "recommended_load_kg": Decimal("60.0"),
                    },
                    {
                        "exercise": exercise_map["Підтягування"],
                        "position": 3,
                        "recommended_sets": 3,
                        "recommended_reps": 6,
                        "recommended_load_kg": Decimal("0.0"),
                    },
                ],
            },
            {
                "name": "Силове тренування Б",
                "category": ExerciseCategory.STRENGTH,
                "description": ("Базовий спліт Б: станова тяга, жим та підтягування."),
                "exercises": [
                    {
                        "exercise": exercise_map["Станова тяга"],
                        "position": 1,
                        "recommended_sets": 4,
                        "recommended_reps": 6,
                        "recommended_load_kg": Decimal("90.0"),
                    },
                    {
                        "exercise": exercise_map["Жим лежачи"],
                        "position": 2,
                        "recommended_sets": 3,
                        "recommended_reps": 10,
                        "recommended_load_kg": Decimal("50.0"),
                    },
                    {
                        "exercise": exercise_map["Підтягування"],
                        "position": 3,
                        "recommended_sets": 3,
                        "recommended_reps": 8,
                        "recommended_load_kg": Decimal("0.0"),
                    },
                ],
            },
            {
                "name": "Функціональний мікс",
                "category": ExerciseCategory.STRENGTH,
                "description": "Функціональне силове кругове тренування.",
                "exercises": [
                    {
                        "exercise": exercise_map["Присідання зі штангою"],
                        "position": 1,
                        "recommended_sets": 4,
                        "recommended_reps": 12,
                        "recommended_load_kg": Decimal("50.0"),
                    },
                    {
                        "exercise": exercise_map["Підтягування"],
                        "position": 2,
                        "recommended_sets": 3,
                        "recommended_reps": 8,
                        "recommended_load_kg": Decimal("0.0"),
                    },
                ],
            },
            {
                "name": "Кардіо сесія Інтервальна",
                "category": ExerciseCategory.CARDIO,
                "description": "Інтервальний кардіо тренінг: скакалка та біг.",
                "exercises": [
                    {
                        "exercise": exercise_map["Стрибки на скакалці"],
                        "position": 1,
                        "recommended_duration_min": Decimal("15.00"),
                    },
                    {
                        "exercise": exercise_map["Біг на біговій доріжці"],
                        "position": 2,
                        "recommended_duration_min": Decimal("25.00"),
                        "recommended_distance_km": Decimal("4.500"),
                    },
                ],
            },
            {
                "name": "Кардіо сесія Витривалість",
                "category": ExerciseCategory.CARDIO,
                "description": (
                    "Тривале аеробне тренування на велотренажері та доріжці."
                ),
                "exercises": [
                    {
                        "exercise": exercise_map["Велотренажер"],
                        "position": 1,
                        "recommended_duration_min": Decimal("30.00"),
                        "recommended_distance_km": Decimal("12.000"),
                    },
                    {
                        "exercise": exercise_map["Біг на біговій доріжці"],
                        "position": 2,
                        "recommended_duration_min": Decimal("20.00"),
                        "recommended_distance_km": Decimal("3.000"),
                    },
                ],
            },
            {
                "name": "Ранкова Хатха-йога",
                "category": ExerciseCategory.YOGA,
                "description": "М'яка практика йоги для гнучкості та відновлення.",
                "exercises": [
                    {
                        "exercise": exercise_map["Розминка та стретчинг"],
                        "position": 1,
                        "recommended_duration_min": Decimal("15.00"),
                    },
                    {
                        "exercise": exercise_map["Хатха-йога"],
                        "position": 2,
                        "recommended_duration_min": Decimal("45.00"),
                    },
                ],
            },
        ]

        workout_map = {}
        for w_spec in workouts_specs:
            workout, created = Workout.objects.get_or_create(
                name=w_spec["name"],
                defaults={
                    "category": w_spec["category"],
                    "description": w_spec["description"],
                    "is_archived": False,
                },
            )
            if not created:
                workout.category = w_spec["category"]
                workout.description = w_spec["description"]
                workout.is_archived = False
                workout.save()

            workout.workout_exercises.all().delete()
            for ex_item in w_spec["exercises"]:
                WorkoutExercise.objects.create(
                    workout=workout,
                    exercise=ex_item["exercise"],
                    position=ex_item["position"],
                    recommended_sets=ex_item.get("recommended_sets"),
                    recommended_reps=ex_item.get("recommended_reps"),
                    recommended_load_kg=ex_item.get("recommended_load_kg"),
                    recommended_duration_min=ex_item.get("recommended_duration_min"),
                    recommended_distance_km=ex_item.get("recommended_distance_km"),
                )

            CatalogPublicationService.validate_persisted_workout(workout)
            workout_map[w_spec["name"]] = workout

        self.stdout.write(
            f"Seeded {len(workout_map)} workouts with validated compositions."
        )

        # 3. Seed 6 Published Program Templates (3 pairs for beginner, 3 workouts/week)
        templates_specs = [
            # Pair 1: Weight Loss (1A has 2 cardio vs 1B has 1 cardio)
            {
                "name": "Кардіо фокус для схуднення (Початківець)",
                "fitness_goal": FitnessGoal.WEIGHT_LOSS,
                "experience_level": ExperienceLevel.BEGINNER,
                "workouts_per_week": 3,
                "description": (
                    "Програма для схуднення з акцентом на кардіо витривалість."
                ),
                "workouts": [
                    {
                        "workout": workout_map["Кардіо сесія Інтервальна"],
                        "position": 1,
                        "suggested_weekday": 1,
                    },
                    {
                        "workout": workout_map["Силове тренування А"],
                        "position": 2,
                        "suggested_weekday": 3,
                    },
                    {
                        "workout": workout_map["Кардіо сесія Витривалість"],
                        "position": 3,
                        "suggested_weekday": 5,
                    },
                ],
            },
            {
                "name": "Базовий мікс для схуднення (Початківець)",
                "fitness_goal": FitnessGoal.WEIGHT_LOSS,
                "experience_level": ExperienceLevel.BEGINNER,
                "workouts_per_week": 3,
                "description": (
                    "Збалансована програма схуднення з перевагою силових навантажень."
                ),
                "workouts": [
                    {
                        "workout": workout_map["Силове тренування А"],
                        "position": 1,
                        "suggested_weekday": 1,
                    },
                    {
                        "workout": workout_map["Кардіо сесія Інтервальна"],
                        "position": 2,
                        "suggested_weekday": 3,
                    },
                    {
                        "workout": workout_map["Силове тренування Б"],
                        "position": 3,
                        "suggested_weekday": 5,
                    },
                ],
            },
            # Pair 2: Muscle Gain (Strength preference: 2A has 3 strength vs 2B has 1)
            {
                "name": "Інтенсивний набір м'язової маси (Початківець)",
                "fitness_goal": FitnessGoal.MUSCLE_GAIN,
                "experience_level": ExperienceLevel.BEGINNER,
                "workouts_per_week": 3,
                "description": (
                    "Чисто силовий триденний спліт для максимальної гіпертрофії."
                ),
                "workouts": [
                    {
                        "workout": workout_map["Силове тренування А"],
                        "position": 1,
                        "suggested_weekday": 1,
                    },
                    {
                        "workout": workout_map["Силове тренування Б"],
                        "position": 2,
                        "suggested_weekday": 3,
                    },
                    {
                        "workout": workout_map["Функціональний мікс"],
                        "position": 3,
                        "suggested_weekday": 5,
                    },
                ],
            },
            {
                "name": "Гібридний ріст м'язів (Початківець)",
                "fitness_goal": FitnessGoal.MUSCLE_GAIN,
                "experience_level": ExperienceLevel.BEGINNER,
                "workouts_per_week": 3,
                "description": (
                    "Гібридна програма: силове тренування, кардіо та йога."
                ),
                "workouts": [
                    {
                        "workout": workout_map["Силове тренування А"],
                        "position": 1,
                        "suggested_weekday": 1,
                    },
                    {
                        "workout": workout_map["Кардіо сесія Витривалість"],
                        "position": 2,
                        "suggested_weekday": 3,
                    },
                    {
                        "workout": workout_map["Ранкова Хатха-йога"],
                        "position": 3,
                        "suggested_weekday": 5,
                    },
                ],
            },
            # Pair 3: Maintenance (Even spread: 3A has 1+1+1 vs 3B has 3 strength)
            {
                "name": "Гармонійний баланс (Початківець)",
                "fitness_goal": FitnessGoal.MAINTENANCE,
                "experience_level": ExperienceLevel.BEGINNER,
                "workouts_per_week": 3,
                "description": (
                    "Ідеальний баланс сили, кардіо та відновлювальної йоги."
                ),
                "workouts": [
                    {
                        "workout": workout_map["Силове тренування А"],
                        "position": 1,
                        "suggested_weekday": 1,
                    },
                    {
                        "workout": workout_map["Кардіо сесія Інтервальна"],
                        "position": 2,
                        "suggested_weekday": 3,
                    },
                    {
                        "workout": workout_map["Ранкова Хатха-йога"],
                        "position": 3,
                        "suggested_weekday": 5,
                    },
                ],
            },
            {
                "name": "Силовий баланс форми (Початківець)",
                "fitness_goal": FitnessGoal.MAINTENANCE,
                "experience_level": ExperienceLevel.BEGINNER,
                "workouts_per_week": 3,
                "description": "Підтримка форми через силове тренування.",
                "workouts": [
                    {
                        "workout": workout_map["Силове тренування А"],
                        "position": 1,
                        "suggested_weekday": 1,
                    },
                    {
                        "workout": workout_map["Силове тренування Б"],
                        "position": 2,
                        "suggested_weekday": 3,
                    },
                    {
                        "workout": workout_map["Функціональний мікс"],
                        "position": 3,
                        "suggested_weekday": 5,
                    },
                ],
            },
        ]

        for t_spec in templates_specs:
            template, created = ProgramTemplate.objects.get_or_create(
                name=t_spec["name"],
                defaults={
                    "fitness_goal": t_spec["fitness_goal"],
                    "experience_level": t_spec["experience_level"],
                    "workouts_per_week": t_spec["workouts_per_week"],
                    "description": t_spec["description"],
                    "status": ProgramTemplateStatus.PUBLISHED,
                },
            )
            if not created:
                template.fitness_goal = t_spec["fitness_goal"]
                template.experience_level = t_spec["experience_level"]
                template.workouts_per_week = t_spec["workouts_per_week"]
                template.description = t_spec["description"]
                template.status = ProgramTemplateStatus.PUBLISHED
                template.save()

            template.program_template_workouts.all().delete()
            for w_item in t_spec["workouts"]:
                ProgramTemplateWorkout.objects.create(
                    program_template=template,
                    workout=w_item["workout"],
                    position=w_item["position"],
                    suggested_weekday=w_item.get("suggested_weekday"),
                )

            CatalogPublicationService.validate_persisted_program_template(template)

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully seeded shared catalog "
                "(10 exercises, 6 workouts, 6 templates)."
            )
        )
