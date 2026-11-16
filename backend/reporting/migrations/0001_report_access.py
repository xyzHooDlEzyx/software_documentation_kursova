from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="ReportAccess",
            fields=[("id", models.BigAutoField(primary_key=True, serialize=False))],
            options={
                "verbose_name": "агрегований звіт",
                "verbose_name_plural": "агреговані звіти",
                "managed": False,
                "default_permissions": (),
                "permissions": (("view_reports", "Can view aggregate reports"),),
            },
        )
    ]
