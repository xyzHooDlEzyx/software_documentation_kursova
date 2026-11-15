from django.contrib.auth.management import create_permissions
from django.db import migrations


PERMISSIONS = (
    "view_challenge",
    "add_challenge",
    "change_challenge",
    "view_achievement",
)


def grant_permissions(apps, schema_editor):
    app_config = apps.get_app_config("engagement")
    app_config.models_module = True
    create_permissions(app_config, apps=apps, verbosity=0)
    app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    group, _ = Group.objects.get_or_create(name="Administrator")
    for codename in PERMISSIONS:
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="engagement", codename=codename
            )
        )


def revoke_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    group = Group.objects.filter(name="Administrator").first()
    if group is not None:
        group.permissions.remove(
            *Permission.objects.filter(
                content_type__app_label="engagement", codename__in=PERMISSIONS
            )
        )


class Migration(migrations.Migration):
    dependencies = [
        ("engagement", "0003_seed_achievements"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]
    operations = [migrations.RunPython(grant_permissions, revoke_permissions)]
