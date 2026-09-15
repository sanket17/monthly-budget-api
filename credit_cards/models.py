from django.db import models
from django.db.models import Q

from .managers import ActiveCreditCardManager


class CreditCard(models.Model):
    """
    A credit card tracked independently from regular expenses (CARD-01/02).
    planned_amount is a STATIC field, overwritten in place on edit — unlike
    budget.models.PlannedAmount there is no append-only carry-forward
    history here (confirmed decision: CARD-02 says "edit", not
    "carries over"/"history" the way BUDG-07/08 explicitly do).

    Soft delete (same pattern as budget.models.Category): deletion sets
    is_active=False, never calls .delete() — see
    credit_cards/views.py CreditCardViewSet.perform_destroy. `objects`
    (ActiveCreditCardManager) excludes is_active=False rows from all
    normal queries — including DRF's auto-inferred PrimaryKeyRelatedField
    queryset for CreditCardEntry.card, so a soft-deleted card can never be
    selected for a new entry. Use `all_objects` to see soft-deleted rows
    too (e.g. in admin).
    """

    user = models.ForeignKey(
        "users.CustomUser", on_delete=models.CASCADE, related_name="credit_cards"
    )
    name = models.CharField(max_length=100)
    planned_amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    objects = ActiveCreditCardManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "credit_cards"
        verbose_name = "credit card"
        verbose_name_plural = "credit cards"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                condition=Q(is_active=True),
                name="unique_active_credit_card_name_per_user",
            ),
        ]

    def __str__(self):
        return self.name


class CreditCardEntry(models.Model):
    """
    A single expense entry on a credit card (CARD-03/04) — deliberately
    separate from transactions.models.Transaction: no category field,
    entries belong to a card, not a budget category. Keeps credit cards
    fully independent of the expense/income category system (PROJECT.md
    decision: "Credit cards tracked separately from expenses").

    card is PROTECTed: even though CreditCard is only ever soft-deleted in
    practice (never .delete()'d — see CreditCardViewSet.perform_destroy),
    PROTECT is the same defense-in-depth precedent already used for
    Category and PlannedAmount/Transaction FKs — a hard delete attempted
    from the shell or a future code path would fail loudly instead of
    silently orphaning or cascading away entries.
    """

    user = models.ForeignKey(
        "users.CustomUser", on_delete=models.CASCADE, related_name="credit_card_entries"
    )
    card = models.ForeignKey(
        "credit_cards.CreditCard", on_delete=models.PROTECT, related_name="entries"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "credit_card_entries"
        verbose_name = "credit card entry"
        verbose_name_plural = "credit card entries"
        indexes = [
            models.Index(fields=["card", "date"], name="idx_cc_entry_card_date"),
        ]
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.card.name} - {self.amount} ({self.date})"
