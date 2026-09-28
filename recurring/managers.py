from django.db import models


class ActiveRecurringEntryManager(models.Manager):
    """Default manager for RecurringEntry — excludes soft-deleted (is_active=False) rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
