from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from budget.utils import parse_month_param
from users.mixins import UserScopedMixin

from .models import CreditCard, CreditCardEntry
from .serializers import CreditCardEntrySerializer, CreditCardSerializer


class CreditCardViewSet(UserScopedMixin, viewsets.ModelViewSet):
    """
    /api/credit-cards/ — CRUD for credit cards (CARD-01/02) plus
    planned-vs-actual per month (CARD-05, via CreditCardSerializer's
    actual_amount field).

    DELETE performs a SOFT delete (is_active=False) — see perform_destroy.
    Never calls CreditCard.delete(): historical CreditCardEntry rows must
    keep referencing the card unchanged (no cascade, no history loss),
    same rationale as budget/views.py CategoryViewSet.perform_destroy.
    """

    queryset = CreditCard.objects.all()
    serializer_class = CreditCardSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["month"] = parse_month_param(self.request)
        return context

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class CreditCardEntryViewSet(UserScopedMixin, viewsets.ModelViewSet):
    """
    /api/credit-card-entries/ — CRUD for credit card expense entries
    (CARD-03/04). Hard delete — no history requirement, same as
    transactions/views.py TransactionViewSet.
    """

    queryset = CreditCardEntry.objects.all()
    serializer_class = CreditCardEntrySerializer
    permission_classes = [IsAuthenticated]
