from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from users.mixins import UserScopedMixin

from .models import CreditCard
from .serializers import CreditCardSerializer


class CreditCardViewSet(UserScopedMixin, viewsets.ModelViewSet):
    """
    /api/credit-cards/ — CRUD for credit cards (CARD-01/02).

    DELETE performs a SOFT delete (is_active=False) — see perform_destroy.
    Never calls CreditCard.delete(): historical CreditCardEntry rows must
    keep referencing the card unchanged (no cascade, no history loss),
    same rationale as budget/views.py CategoryViewSet.perform_destroy.
    """

    queryset = CreditCard.objects.all()
    serializer_class = CreditCardSerializer
    permission_classes = [IsAuthenticated]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
