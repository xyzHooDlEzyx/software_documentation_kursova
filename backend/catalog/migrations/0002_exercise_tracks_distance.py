"""Add ``Exercise.tracks_distance``.

Before this field any cardio exercise could carry a distance (e.g. rope
jumping). Existing data stays valid: cardio exercises that already have a
recommended distance in the shared catalog or in a personal program copy are
marked as distance-tracking; everything else defaults to duration only.
"""

from django.db import migrations, models


def mark_existing_distance_exercises(apps, schema_editor):
    Exercise = apps.get_model("catalog", "Exercise")
    WorkoutExercise = apps.get_model("catalog", "WorkoutExercise")
    UserProgramExercise = apps.get_model("planning", "UserProgramExercise")
    used_with_distance = set(
        WorkoutExercise.objects.filter(recommended_distance_km__isnull=False).values_list(
            "exercise_id", flat=True
        )
    ) | set(
        UserProgramExercise.objects.filter(
            recommended_distance_km__isnull=False
        ).values_list("exercise_id", flat=True)
    )
    Exercise.objects.filter(pk__in=used_with_distance, category="cardio").update(
        tracks_distance=True
    )


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
        ("planning", "0002_align_user_program_with_erd"),
    ]

    operations = [
        migrations.AddField(
            model_name="exercise",
            name="tracks_distance",
            field=models.BooleanField(
                db_default=False,
                default=False,
                help_text=(
                    "Лише для кардіо: чи має вправа дистанцію (біг, велосипед). "
                    "Для скакалки тощо — лише тривалість."
                ),
                verbose_name="Вимірюється дистанцією",
            ),
        ),
        migrations.RunPython(
            mark_existing_distance_exercises, reverse_code=migrations.RunPython.noop
        ),
        migrations.AddConstraint(
            model_name="exercise",
            constraint=models.CheckConstraint(
                condition=models.Q(("tracks_distance", False), ("category", "cardio"), _connector="OR"),
                name="exercises_distance_only_cardio",
            ),
        ),
    ]
