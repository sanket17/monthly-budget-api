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
