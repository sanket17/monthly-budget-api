import calendar

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from budget.utils import parse_month_param
from users.mixins import UserScopedMixin

from .models import InitialBalance, Transaction
from .pagination import TransactionPagination
from .serializers import InitialBalanceSerializer, TransactionSerializer


class TransactionViewSet(UserScopedMixin, viewsets.ModelViewSet):
    """
    /api/transactions/ — CRUD for expense and income transactions
    (TXNS-01..07). Always scoped to a single calendar month: ?month=YYYY-MM
    (or YYYY-MM-DD) selects the month (TXNS-05/06); omitting it defaults to
    the current month, matching the calendar-month budget period (CLAUDE.md
    data model constraint) and budget/views.py CategoryViewSet's
    planned_amount default.
    """

    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TransactionPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        month_start = parse_month_param(self.request)
        _, last_day = calendar.monthrange(month_start.year, month_start.month)
        month_end = month_start.replace(day=last_day)
        return queryset.filter(date__gte=month_start, date__lte=month_end)


class InitialBalanceViewSet(UserScopedMixin, viewsets.ModelViewSet):
    """
    /api/initial-balances/ — set the bank and emergency-fund starting
    balances (BALN-01/03). No PUT/PATCH/DELETE — re-POSTing upserts (see
    InitialBalanceSerializer.create), same append-vs-replace-in-serializer
    approach as budget/views.py PlannedAmountViewSet.
    """

    queryset = InitialBalance.objects.all()
    serializer_class = InitialBalanceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
