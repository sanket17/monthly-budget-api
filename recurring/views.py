from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.mixins import UserScopedMixin

from .models import RecurringEntry
from .serializers import RecurringEntrySerializer


class RecurringEntryViewSet(UserScopedMixin, viewsets.ModelViewSet):
    """
    /api/recurring-entries/ — CRUD for recurring expense/income entries
    (RECR-01/02), minus reactivation (Plan 06-02's job).

    DELETE performs a SOFT delete (is_active=False) — see perform_destroy.
    Never calls RecurringEntry.delete(): RecurringGenerationLog rows (and
    the historical Transactions they represent) must keep referencing the
    entry unchanged, same rationale as
    credit_cards/views.py::CreditCardViewSet.perform_destroy.
    """

    queryset = RecurringEntry.objects.all()
    serializer_class = RecurringEntrySerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
