import calendar

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from budget.utils import parse_month_param
from users.mixins import UserScopedMixin

from .models import Transaction
from .pagination import TransactionPagination
from .serializers import TransactionSerializer


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
