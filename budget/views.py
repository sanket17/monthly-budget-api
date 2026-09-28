from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from users.mixins import UserScopedMixin

from .models import Category, PlannedAmount
from .serializers import CategorySerializer, PlannedAmountSerializer
from .utils import parse_month_param


class CategoryViewSet(UserScopedMixin, viewsets.ModelViewSet):
    """
    /api/categories/ — CRUD for expense and income categories (BUDG-01..04).

    DELETE performs a SOFT delete (is_active=False) — see perform_destroy.
    Never calls Category.delete(): historical PlannedAmount rows must
    keep referencing the category unchanged (D-01, no cascade, no history
    loss).
    """

    # Category.objects is ActiveCategoryManager (budget/models.py) — already
    # excludes is_active=False rows. Do NOT add .filter(is_active=True) here
    # too (PATTERNS.md flagged double-filtering across manager + viewset).
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["month"] = parse_month_param(self.request)
        return context

    def perform_destroy(self, instance):
        # D-15: a category referenced by an active RecurringEntry cannot be
        # soft-deleted — reject before touching is_active. instance is
        # already scoped to request.user via UserScopedMixin, so this check
        # only ever inspects the requester's own reverse relation (never a
        # cross-user information leak, see 06-RESEARCH.md T-06-09).
        if instance.recurring_entries.filter(is_active=True).exists():
            raise ValidationError(
                "Cannot delete a category referenced by an active recurring "
                "entry. Change or delete the recurring entry first."
            )
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class PlannedAmountViewSet(UserScopedMixin, viewsets.ModelViewSet):
    """
    /api/planned-amounts/ — set and list planned amounts (BUDG-05..08).

    Append-only (D-08): no PUT/PATCH/DELETE — editing is done by POSTing a
    new PlannedAmount; PlannedAmountSerializer.create() decides
    append-vs-update-in-place per D-08's future-dated-row rule. Exposing
    PUT/PATCH/DELETE here would let a client silently mutate or destroy
    history, breaking BUDG-08's "changing a planned amount does not alter
    historical months" guarantee.
    """

    queryset = PlannedAmount.objects.all()
    serializer_class = PlannedAmountSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
