from django.db import migrations


ACHIEVEMENTS = (
    (
        "first_workout",
        "Перше тренування",
        "Завершіть перше тренування.",
    ),
    (
        "five_workouts",
        "П'ять тренувань",
        "Завершіть п'ять тренувань.",
    ),
    (
        "one_hundred_minutes",
        "100 хвилин",
        "Тренуйтеся сумарно щонайменше 100 хвилин.",
    ),
    (
        "marathoner",
        "Марафонець",
        "Подолайте сумарно щонайменше 42,2 км у кардіовправах.",
    ),
    (
        "heavyweight",
        "Важковаговик",
        "Виконайте силову вправу з навантаженням щонайменше 100 кг.",
    ),
)


def seed_achievements(apps, schema_editor):
    Achievement = apps.get_model("engagement", "Achievement")
    for code, name, description in ACHIEVEMENTS:
        Achievement.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "description": description,
                "rule_code": code,
                "is_archived": False,
            },
        )


def unseed_achievements(apps, schema_editor):
    Achievement = apps.get_model("engagement", "Achievement")
    Achievement.objects.filter(code__in=[item[0] for item in ACHIEVEMENTS]).delete()


class Migration(migrations.Migration):
    dependencies = [("engagement", "0002_initial")]
    operations = [migrations.RunPython(seed_achievements, unseed_achievements)]
