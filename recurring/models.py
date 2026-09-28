from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .managers import ActiveRecurringEntryManager


class RecurringEntry(models.Model):
    """
    A monthly recurring expense or income entry (RECR-01/02) that
    auto-generates a real Transaction on its scheduled day each month.
    There is no separate income/expense flag here — category_type
    discriminates, same as Transaction already does (category.category_type).

    day_of_month accepts the full 1-31 range (D-01); when a target month
    has fewer days than day_of_month (e.g. 31 in February), generation
    fires on that month's actual last day instead of skipping it — see
    recurring/services.py::scheduled_date_for.

    Soft delete (same pattern as budget.models.Category and
    credit_cards.models.CreditCard): deletion sets is_active=False, never
    calls .delete() — see recurring/views.py
    RecurringEntryViewSet.perform_destroy. `objects`
    (ActiveRecurringEntryManager) excludes is_active=False rows from all
    normal queries; use `all_objects` to see soft-deleted rows too (e.g.
    in admin). Editing day_of_month mid-month only affects future
    generation (D-12) — enforced entirely by RecurringGenerationLog's
    (recurring_entry, period) key, not by anything on this model.
    """

    user = models.ForeignKey(
        "users.CustomUser", on_delete=models.CASCADE, related_name="recurring_entries"
    )
    category = models.ForeignKey(
        "budget.Category", on_delete=models.PROTECT, related_name="recurring_entries"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255)
    day_of_month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ActiveRecurringEntryManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "recurring_entries"
        verbose_name = "recurring entry"
        verbose_name_plural = "recurring entries"
        ordering = ["id"]

    def __str__(self):
        return f"{self.description} - {self.amount} (day {self.day_of_month})"


class RecurringGenerationLog(models.Model):
    """
    A stored fact about a past generation run: one row per
    (recurring_entry, period) that has successfully generated a
    Transaction. This is the FIRST "stored fact about a past batch run"
    model in this codebase — every other model here follows a
    recompute-on-read convention (e.g. transactions/services.py
    get_bank_balance/get_emergency_fund_balance walk forward fresh on
    every read). This deliberate exception exists solely because of D-19:
    idempotency must survive a manually deleted Transaction — if we
    instead checked "does a Transaction already exist for this
    (entry, period)", deleting a generated Transaction would make the
    next generation run silently recreate it, which is never what a user
    deleting a transaction means.

    The DB UniqueConstraint below (not an app-level pre-check) is the
    actual concurrency-safety guarantee — see
    recurring/services.py::_generate_one.
    """

    recurring_entry = models.ForeignKey(
        "recurring.RecurringEntry",
        on_delete=models.CASCADE,
        related_name="generation_log",
    )
    period = models.DateField()
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recurring_generation_log"
        verbose_name = "recurring generation log"
        verbose_name_plural = "recurring generation logs"
        constraints = [
            models.UniqueConstraint(
                fields=["recurring_entry", "period"],
                name="unique_generation_per_entry_period",
            ),
        ]

    def __str__(self):
        return f"{self.recurring_entry_id} - {self.period}"
