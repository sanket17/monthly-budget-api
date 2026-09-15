from django.db import models


class ActiveCreditCardManager(models.Manager):
    """Default manager for CreditCard — excludes soft-deleted (is_active=False) rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
