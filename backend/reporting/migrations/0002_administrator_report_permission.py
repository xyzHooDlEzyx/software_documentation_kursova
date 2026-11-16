from django.contrib.auth.management import create_permissions
from django.db import migrations


def grant_permission(apps, schema_editor):
    app_config = apps.get_app_config("reporting")
    app_config.models_module = True
    create_permissions(app_config, apps=apps, verbosity=0)
    app_config.models_module = None
    group, _ = apps.get_model("auth", "Group").objects.get_or_create(name="Administrator")
    permission = apps.get_model("auth", "Permission").objects.get(
        content_type__app_label="reporting", codename="view_reports"
    )
    group.permissions.add(permission)


def revoke_permission(apps, schema_editor):
    group = apps.get_model("auth", "Group").objects.filter(name="Administrator").first()
    if group:
        group.permissions.remove(
            *apps.get_model("auth", "Permission").objects.filter(
                content_type__app_label="reporting", codename="view_reports"
            )
        )


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0001_report_access"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]
    operations = [migrations.RunPython(grant_permission, revoke_permission)]
