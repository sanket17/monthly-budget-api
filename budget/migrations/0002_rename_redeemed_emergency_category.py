# Data migration (D-02): rename the seeded income category from
# "Redeemed Emergency" (Phase 2's actual seeded value) to
# "Redeem Emergency Fund" (the roadmap/requirements wording), in place,
# for every existing user.
#
# Uses the historical model via apps.get_model, which sees ALL rows
# (active and soft-deleted) since it bypasses ActiveCategoryManager —
# matches D-02's "in place, for all existing users" with no
# active-only qualifier.
#
# NEVER `from budget.constants import ...` here — migrations must stay
# correct even after the constant changes in a later commit (Task 2).
# Literals are duplicated intentionally.
#
# Renames row-by-row inside its own transaction.atomic() savepoint,
# rather than one blind bulk .update(), because a single user already
# having an active "Redeem Emergency Fund" income category would
# collide with Category's unique_active_category_name_per_user_type
# constraint and abort the whole migration for every other user
# (RESEARCH.md Pitfall 4). A collision is caught per-row and logged
# instead of raised.

from django.db import migrations, transaction
from django.db.utils import IntegrityError

OLD_NAME = "Redeemed Emergency"
NEW_NAME = "Redeem Emergency Fund"


def rename_forward(apps, schema_editor):
    Category = apps.get_model("budget", "Category")
    db_alias = schema_editor.connection.alias
    queryset = Category.objects.using(db_alias).filter(
        category_type="income", name__iexact=OLD_NAME
    )
    for category in queryset:
        try:
            with transaction.atomic(using=db_alias):
                category.name = NEW_NAME
                category.save(using=db_alias, update_fields=["name"])
        except IntegrityError:
            print(
                f"WARNING: skipped renaming Category id={category.id} "
                f"user_id={category.user_id} name={category.name!r} to "
                f"{NEW_NAME!r} — active category with that name already "
                f"exists for this user (collision)."
            )


def rename_reverse(apps, schema_editor):
    Category = apps.get_model("budget", "Category")
    db_alias = schema_editor.connection.alias
    queryset = Category.objects.using(db_alias).filter(
        category_type="income", name__iexact=NEW_NAME
    )
    for category in queryset:
        try:
            with transaction.atomic(using=db_alias):
                category.name = OLD_NAME
                category.save(using=db_alias, update_fields=["name"])
        except IntegrityError:
            print(
                f"WARNING: skipped reverting Category id={category.id} "
                f"user_id={category.user_id} name={category.name!r} to "
                f"{OLD_NAME!r} — active category with that name already "
                f"exists for this user (collision)."
            )


class Migration(migrations.Migration):

    dependencies = [
        ("budget", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(rename_forward, rename_reverse),
    ]
