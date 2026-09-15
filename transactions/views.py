import calendar

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from budget.utils import parse_month_param
from users.mixins import UserScopedMixin

from .models import InitialBalance, Transaction
from .pagination import TransactionPagination
from .serializers import InitialBalanceSerializer, TransactionSerializer
from .services import get_bank_balance, get_emergency_fund_balance


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


class BalanceSummaryView(APIView):
    """
    GET /api/balance/?month=YYYY-MM — opening/closing bank balance and
    emergency-fund balance for the given month (BALN-02, BALN-06).
    Defaults to the current month if ?month= is omitted, same convention
    as TransactionViewSet.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        month_start = parse_month_param(request)
        return Response(
            {
                "month": month_start,
                "bank_balance": get_bank_balance(request.user.id, month_start),
                "emergency_fund_balance": get_emergency_fund_balance(
                    request.user.id, month_start
                ),
            }
        )
