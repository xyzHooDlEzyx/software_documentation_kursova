"""Upgrade checks for the Phase 4 personal-program schema correction."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder

OLD_SCHEMA = [("planning", "0001_initial")]
NEW_SCHEMA = [("planning", "0002_align_user_program_with_erd")]


@pytest.fixture
def planning_0001(transactional_db):
    """Use the historical planning schema, then restore the current test schema."""
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes("planning")
    executor.migrate(OLD_SCHEMA)
    old_apps = executor.loader.project_state(OLD_SCHEMA).apps

    try:
        yield old_apps
    finally:
        applied = MigrationRecorder(connection).applied_migrations()
        if NEW_SCHEMA[0] not in applied:
            # A rejection test deliberately leaves the old schema in place.
            old_apps.get_model("planning", "UserProgram").objects.filter(
                bonus_points_awarded=True
            ).update(bonus_points_awarded=False)
        MigrationExecutor(connection).migrate(latest)


def create_historical_program(old_apps, *, bonus_points_awarded=False):
    User = old_apps.get_model("accounts", "User")
    Template = old_apps.get_model("catalog", "ProgramTemplate")
    UserProgram = old_apps.get_model("planning", "UserProgram")

    user = User.objects.create(
        email="migration-athlete@example.test", password="unusable-migration-test"
    )
    template = Template.objects.create(
        name="Original template",
        fitness_goal="weight_loss",
        experience_level="beginner",
        workouts_per_week=3,
        status="archived",
    )
    program = UserProgram.objects.create(
        user=user,
        source_program_template=template,
        source_program_template_name_snapshot="Original template",
        name="Personal copy",
        status="draft",
        bonus_points_awarded=bonus_points_awarded,
    )
    return user, template, program


def test_0002_backfills_goal_and_preserves_existing_draft(planning_0001):
    user, template, program = create_historical_program(planning_0001)

    executor = MigrationExecutor(connection)
    executor.migrate(NEW_SCHEMA)
    upgraded_apps = executor.loader.project_state(NEW_SCHEMA).apps
    upgraded = upgraded_apps.get_model("planning", "UserProgram").objects.get(
        pk=program.pk
    )

    assert upgraded.pk == program.pk
    assert upgraded.user_id == user.pk
    assert upgraded.source_program_template_id == template.pk
    assert upgraded.fitness_goal == "weight_loss"
    assert upgraded.source_program_template_name_snapshot == "Original template"
    assert upgraded.name == "Personal copy"
    assert upgraded.status == "draft"
    assert upgraded.activated_at is None
    assert upgraded.bonus_target_sessions is None
    assert upgraded.completed_at is None
    assert upgraded.total_planned_at_completion is None
    assert upgraded.completed_planned_at_completion is None
    assert upgraded.progress_percent_at_completion is None


def test_0002_rejects_unmappable_legacy_bonus_data(planning_0001):
    _, _, program = create_historical_program(planning_0001, bonus_points_awarded=True)

    with pytest.raises(RuntimeError, match="Cannot discard legacy UserProgram"):
        MigrationExecutor(connection).migrate(NEW_SCHEMA)

    assert NEW_SCHEMA[0] not in MigrationRecorder(connection).applied_migrations()
    historical = planning_0001.get_model("planning", "UserProgram").objects.get(
        pk=program.pk
    )
    assert historical.bonus_points_awarded is True

    historical.bonus_points_awarded = False
    historical.save(update_fields=["bonus_points_awarded"])
    MigrationExecutor(connection).migrate(NEW_SCHEMA)
