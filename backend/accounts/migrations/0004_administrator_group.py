"""Create the ``Administrator`` group used by the admin part of the system.

Permissions are created by Django's ``post_migrate`` signal, which has not run
yet on a fresh database, so they are created explicitly before assignment.
"""

from django.contrib.auth.management import create_permissions
from django.db import migrations

GROUP_NAME = "Administrator"

PERMISSIONS = [
    ("accounts", "deactivate_user"),
    ("catalog", "view_exercise"),
    ("catalog", "add_exercise"),
    ("catalog", "change_exercise"),
    ("catalog", "view_workout"),
    ("catalog", "add_workout"),
    ("catalog", "change_workout"),
    ("catalog", "view_programtemplate"),
    ("catalog", "add_programtemplate"),
    ("catalog", "change_programtemplate"),
]


def create_administrator_group(apps, schema_editor):
    for app_label in ("accounts", "catalog"):
        app_config = apps.get_app_config(app_label)
        # Migration AppConfigStub has no models_module; create_permissions
        # skips such configs, so mark it temporarily as having models.
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    for app_label, codename in PERMISSIONS:
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label=app_label, codename=codename
            )
        )


def remove_administrator_group(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name=GROUP_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_profile_weightentry"),
        ("catalog", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_administrator_group, remove_administrator_group)
    ]
