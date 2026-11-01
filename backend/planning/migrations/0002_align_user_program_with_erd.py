"""Align personal-program state and snapshots with the approved ERD.

Phase 4 can persist draft copies only. Existing drafts retain their data and
receive a frozen goal from their source template. Legacy bonus/snapshot data
cannot be translated into the approved ledger and progress snapshot safely,
so the migration refuses to discard such data.
"""

from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


def reject_unmappable_legacy_data(apps, schema_editor):
    UserProgram = apps.get_model("planning", "UserProgram")
    programs = UserProgram.objects.using(schema_editor.connection.alias)
    if programs.filter(source_program_template_id__isnull=True).exists():
        raise RuntimeError(
            "Cannot require a source template: a UserProgram has no source. "
            "Repair that row before applying planning.0002."
        )

    legacy_data = (
        models.Q(bonus_points_awarded=True)
        | models.Q(completion_snapshot_completed_sessions_count__isnull=False)
        | models.Q(completion_snapshot_bonus_target_sessions__isnull=False)
        | models.Q(completion_snapshot_completion_percentage__isnull=False)
        | models.Q(completion_snapshot_points_awarded__isnull=False)
        | models.Q(completion_snapshot_closed_at__isnull=False)
    )
    if programs.filter(legacy_data).exists():
        raise RuntimeError(
            "Cannot discard legacy UserProgram bonus/snapshot data: no "
            "lossless mapping to the approved ledger and completion fields "
            "exists. Repair or migrate those rows before planning.0002."
        )


def backfill_fitness_goal(apps, schema_editor):
    UserProgram = apps.get_model("planning", "UserProgram")
    programs = UserProgram.objects.using(schema_editor.connection.alias)
    for program_id, goal in programs.values_list(
        "pk", "source_program_template__fitness_goal"
    ).iterator(chunk_size=500):
        if goal is None:
            raise RuntimeError(f"UserProgram {program_id} has no source fitness goal.")
        programs.filter(pk=program_id).update(fitness_goal=goal)


class Migration(migrations.Migration):
    dependencies = [("planning", "0001_initial")]

    operations = [
        migrations.RunPython(
            reject_unmappable_legacy_data, reverse_code=migrations.RunPython.noop
        ),
        migrations.AddField(
            model_name="userprogram",
            name="fitness_goal",
            field=models.CharField(
                choices=[
                    ("weight_loss", "weight_loss"),
                    ("muscle_gain", "muscle_gain"),
                    ("maintenance", "maintenance"),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="userprogram",
            name="total_planned_at_completion",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprogram",
            name="completed_planned_at_completion",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprogram",
            name="progress_percent_at_completion",
            field=models.DecimalField(
                blank=True, decimal_places=1, max_digits=5, null=True
            ),
        ),
        migrations.RunPython(
            backfill_fitness_goal, reverse_code=migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="userprogram",
            name="fitness_goal",
            field=models.CharField(
                choices=[
                    ("weight_loss", "weight_loss"),
                    ("muscle_gain", "muscle_gain"),
                    ("maintenance", "maintenance"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="userprogram",
            name="source_program_template",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="user_programs",
                to="catalog.programtemplate",
            ),
        ),
        migrations.RemoveField(model_name="userprogram", name="bonus_points_awarded"),
        migrations.RemoveField(
            model_name="userprogram",
            name="completion_snapshot_completed_sessions_count",
        ),
        migrations.RemoveField(
            model_name="userprogram", name="completion_snapshot_bonus_target_sessions"
        ),
        migrations.RemoveField(
            model_name="userprogram", name="completion_snapshot_completion_percentage"
        ),
        migrations.RemoveField(
            model_name="userprogram", name="completion_snapshot_points_awarded"
        ),
        migrations.RemoveField(
            model_name="userprogram", name="completion_snapshot_closed_at"
        ),
        migrations.AddConstraint(
            model_name="userprogram",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    fitness_goal__in=["weight_loss", "muscle_gain", "maintenance"]
                ),
                name="user_programs_goal_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="userprogram",
            constraint=models.CheckConstraint(
                condition=models.Q(status="draft", activated_at__isnull=True)
                | models.Q(
                    status__in=["active", "completed"], activated_at__isnull=False
                ),
                name="user_programs_activation_state",
            ),
        ),
        migrations.AddConstraint(
            model_name="userprogram",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    activated_at__isnull=True, bonus_target_sessions__isnull=True
                )
                | (
                    models.Q(activated_at__isnull=False)
                    & models.Q(bonus_target_sessions__gte=3)
                ),
                name="user_programs_bonus_target_state",
            ),
        ),
        migrations.AddConstraint(
            model_name="userprogram",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    completed_at__isnull=True,
                    total_planned_at_completion__isnull=True,
                    completed_planned_at_completion__isnull=True,
                    progress_percent_at_completion__isnull=True,
                )
                | models.Q(
                    completed_at__isnull=False,
                    total_planned_at_completion__isnull=False,
                    completed_planned_at_completion__isnull=False,
                    progress_percent_at_completion__isnull=False,
                ),
                name="user_programs_snapshot_all_or_none",
            ),
        ),
        migrations.AddConstraint(
            model_name="userprogram",
            constraint=models.CheckConstraint(
                condition=models.Q(status="completed", completed_at__isnull=False)
                | (~models.Q(status="completed") & models.Q(completed_at__isnull=True)),
                name="user_programs_completion_state",
            ),
        ),
        migrations.AddConstraint(
            model_name="userprogram",
            constraint=models.CheckConstraint(
                condition=~models.Q(status="completed")
                | (
                    models.Q(total_planned_at_completion__gt=0)
                    & models.Q(
                        completed_planned_at_completion=models.F(
                            "total_planned_at_completion"
                        )
                    )
                    & models.Q(progress_percent_at_completion=Decimal("100.0"))
                ),
                name="user_programs_completion_values",
            ),
        ),
    ]
