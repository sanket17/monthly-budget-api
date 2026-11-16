from django.db import migrations, models
from django.utils import timezone


def backfill_deactivated_on(apps, schema_editor):
    """
    Rows soft-deleted before this column existed have no recorded date.
    Stamp them with the migration date: their planned amounts keep counting
    for every month up to now (unchanged history) and stop afterwards.
    """
    Category = apps.get_model("budget", "Category")
    # _base_manager: sees soft-deleted rows even if a real (active-only) default
    # manager is passed in, as the migration test does.
    Category._base_manager.filter(is_active=False, deactivated_on__isnull=True).update(
        deactivated_on=timezone.now().date()
    )


class Migration(migrations.Migration):

    dependencies = [
        ("budget", "0002_rename_redeemed_emergency_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="deactivated_on",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_deactivated_on, migrations.RunPython.noop),
    ]
