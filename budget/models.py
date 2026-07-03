from django.db import models
from django.db.models import Q

from .managers import ActiveCategoryManager


class Category(models.Model):
    """
    Expense or income category, optionally grouped (expense only).

    CRITICAL: group is NULL iff category_type == INCOME — enforced by the
    group_required_iff_expense CheckConstraint below. Never rely on
    serializer validation alone; the DB constraint is the last line of
    defense against a bad data migration, admin edit, or shell command.

    Soft delete (D-01): deletion sets is_active=False, never calls
    .delete(). See budget/views.py CategoryViewSet.perform_destroy.
    `objects` (ActiveCategoryManager) excludes is_active=False rows from
    all normal queries; use `all_objects` to see soft-deleted rows too
    (e.g. in admin).
    """

    class CategoryType(models.TextChoices):
        EXPENSE = "expense", "Expense"
        INCOME = "income", "Income"

    class Group(models.TextChoices):
        NEEDS = "needs", "Needs"
        WANTS = "wants", "Wants"
        INVESTMENT = "investment", "Investment"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        "users.CustomUser", on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=CategoryType.choices)
    group = models.CharField(
        max_length=12, choices=Group.choices, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    objects = ActiveCategoryManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "categories"
        verbose_name = "category"
        verbose_name_plural = "categories"
        constraints = [
            models.CheckConstraint(
                # Django >= 5.1: use `condition=`, NEVER `check=` (deprecated,
                # RemovedInDjango60Warning — see 02-RESEARCH.md Pitfall 4).
                condition=(
                    Q(category_type="expense", group__isnull=False)
                    | Q(category_type="income", group__isnull=True)
                ),
                name="group_required_iff_expense",
            ),
            models.UniqueConstraint(
                # D-07: duplicate active category names (same user, same
                # category_type) are rejected at the DB level. Soft-deleted
                # (is_active=False) categories don't block reuse of the name.
                fields=["user", "category_type", "name"],
                condition=Q(is_active=True),
                name="unique_active_category_name_per_user_type",
            ),
        ]

    def __str__(self):
        return self.name


class PlannedAmount(models.Model):
    """
    Append-only carry-forward planned amount for a Category, per month
    (BUDG-05..08).

    CRITICAL (D-08): Never UPDATE or DELETE a row once its effective_from
    has taken effect (i.e. is <= the current month's start). Every change
    to an already-effective row is a NEW row with a later effective_from.
    "Current" value for a given month = latest row with
    effective_from <= that month's start (see budget/services.py
    get_effective_amount). The ONE exception: if the most recent row's
    effective_from is still in the FUTURE relative to today, editing
    again updates that same row in place instead of appending — this
    exception is implemented in budget/serializers.py
    PlannedAmountSerializer.create(), not here in the model.
    """

    # Denormalized from category.user — REQUIRED so UserScopedMixin.get_queryset()
    # (which filters .filter(user=self.request.user)) works unmodified, per
    # Phase 1's established mixin contract. Do not remove even though it
    # duplicates category.user (02-RESEARCH.md Pitfall 1).
    user = models.ForeignKey(
        "users.CustomUser", on_delete=models.CASCADE, related_name="planned_amounts"
    )
    category = models.ForeignKey(
        "budget.Category", on_delete=models.PROTECT, related_name="planned_amounts"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    effective_from = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "planned_amounts"
        verbose_name = "planned amount"
        verbose_name_plural = "planned amounts"
        indexes = [
            models.Index(
                fields=["category", "-effective_from"],
                name="idx_category_effective_from",
            ),
        ]
        ordering = ["-effective_from", "-created_at"]

    def __str__(self):
        return f"{self.category.name} - {self.amount} (from {self.effective_from})"
