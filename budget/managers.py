from django.db import models


class ActiveCategoryManager(models.Manager):
    """Default manager for Category — excludes soft-deleted (is_active=False) rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
