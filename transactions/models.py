from django.db import models


class Transaction(models.Model):
    """
    A single expense or income entry (TXNS-01..04). There is no separate
    "type" field — a transaction's type is whatever type its category is
    (budget.models.Category.category_type). category is PROTECTed so a
    category can never be deleted (even soft-deleted categories stay
    queryable via Category.all_objects) while transactions still
    reference it — historical transactions must never lose their category.
    """

    user = models.ForeignKey(
        "users.CustomUser", on_delete=models.CASCADE, related_name="transactions"
    )
    category = models.ForeignKey(
        "budget.Category", on_delete=models.PROTECT, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transactions"
        verbose_name = "transaction"
        verbose_name_plural = "transactions"
        indexes = [
            models.Index(fields=["user", "date"], name="idx_transaction_user_date"),
        ]
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.category.name} - {self.amount} ({self.date})"


class InitialBalance(models.Model):
    """
    Anchor point for balance calculation (BALN-01/03): the amount the user
    is starting with, and the calendar month it applies from. One row per
    (user, balance_type) — re-setting it (InitialBalanceSerializer.create)
    updates the existing row in place rather than appending a new one;
    unlike budget.models.PlannedAmount there is no history requirement
    here, so no append-only carry-forward pattern is needed.

    balance_type discriminates bank vs emergency_fund, following the same
    discriminator pattern as budget.models.Category (category_type)
    instead of two near-identical models.
    """

    class BalanceType(models.TextChoices):
        BANK = "bank", "Bank"
        EMERGENCY_FUND = "emergency_fund", "Emergency Fund"

    user = models.ForeignKey(
        "users.CustomUser", on_delete=models.CASCADE, related_name="initial_balances"
    )
    balance_type = models.CharField(max_length=20, choices=BalanceType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    effective_month = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "initial_balances"
        verbose_name = "initial balance"
        verbose_name_plural = "initial balances"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "balance_type"],
                name="unique_initial_balance_per_user_type",
            ),
        ]

    def __str__(self):
        return f"{self.get_balance_type_display()} - {self.amount} (from {self.effective_month})"
