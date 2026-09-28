from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from budget.utils import parse_month_param

from .services import get_dashboard


class DashboardView(APIView):
    """
    GET /api/dashboard/?month=YYYY-MM — single authoritative aggregation
    endpoint (D-12) composing bank/emergency-fund balances, savings, and
    planned-vs-actual totals for the given month. Defaults to the current
    month if ?month= is omitted, same convention as BalanceSummaryView.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        month_start = parse_month_param(request)
        # BOLA defense — always request.user.id, never a query param or
        # request-body value (users/mixins.py::UserScopedMixin's rule,
        # applied manually here since DashboardView is a plain APIView).
        return Response(get_dashboard(request.user.id, month_start))
