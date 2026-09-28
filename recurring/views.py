from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from transactions.serializers import TransactionSerializer
from users.mixins import UserScopedMixin

from .models import RecurringEntry
from .serializers import RecurringEntrySerializer
from .services import generate_for_user, today_for_user


class RecurringEntryViewSet(UserScopedMixin, viewsets.ModelViewSet):
    """
    /api/recurring-entries/ — CRUD for recurring expense/income entries
    (RECR-01/02), plus reactivation of a soft-deleted entry (D-17, see
    the `reactivate` action below).

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

    @action(detail=True, methods=["patch"])
    def reactivate(self, request, pk=None):
        """
        D-17: flips a soft-deleted entry's is_active back to True so
        generation resumes from its next occurrence.

        Queries RecurringEntry.all_objects (not the active-only default
        manager `objects`) because a soft-deleted row is exactly what this
        action must be able to reach — every other action on this
        ViewSet correctly keeps soft-deleted rows out via the normal
        `queryset = RecurringEntry.objects.all()`.

        T-06-06 (BOLA): bypassing get_queryset() to use all_objects means
        UserScopedMixin's normal scoping does not apply automatically here,
        so `user=request.user` is re-asserted explicitly — a crafted pk
        belonging to another user 404s instead of leaking existence.
        """
        instance = get_object_or_404(
            RecurringEntry.all_objects, pk=pk, user=request.user
        )
        instance.is_active = True
        instance.save(update_fields=["is_active"])
        return Response(self.get_serializer(instance).data)


class GenerateRecurringEntriesView(APIView):
    """
    POST /api/recurring-entries/generate/ — on-demand generation for all of
    the caller's active recurring entries, current month only (D-22..26).

    Deliberately sets no throttle_classes/throttle_scope override (D-25) —
    inherits the project's default user throttle (1000/day) rather than the
    5/min `auth` scope used on register/login: the operation is idempotent
    and strictly user-scoped, so there is no credential-stuffing-style
    abuse vector to bound more tightly.

    T-06-05 (BOLA): this is a plain APIView, not a ModelViewSet, so
    UserScopedMixin does not attach automatically. Scoping is structural
    instead — request.data and request.query_params are never read here at
    all (D-23), so there is no entry-id/user-id/month parameter to
    validate or reject in the first place. Every input flows from
    request.user alone into generate_for_user(request.user, ...), which
    only ever touches user.recurring_entries.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_month = today_for_user(request.user).replace(day=1)
        created = generate_for_user(request.user, upto_month=current_month)
        return Response(TransactionSerializer(created, many=True).data)
