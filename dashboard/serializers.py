"""
Response serializers for GET /api/dashboard/ — used ONLY to describe the
payload built by dashboard.services.get_dashboard in the OpenAPI schema
(G5). Nothing validates input or renders output through them.
"""

from rest_framework import serializers

from budget.models import Category
from transactions.serializers import BalanceSnapshotSerializer

MONEY = {"max_digits": 14, "decimal_places": 2}
# Ratios are unrounded Decimals (see 05-REVIEW.md IN-02); null when the
# denominator is zero/absent (D-09, D-10).
RATIO = {"max_digits": 30, "decimal_places": 20, "allow_null": True}


class SavingsSerializer(serializers.Serializer):
    start_balance = serializers.DecimalField(allow_null=True, **MONEY)
    end_balance = serializers.DecimalField(allow_null=True, **MONEY)
    percentage = serializers.DecimalField(**RATIO)
    amount = serializers.DecimalField(allow_null=True, **MONEY)


class ExpenseBreakdownItemSerializer(serializers.Serializer):
    group = serializers.ChoiceField(choices=Category.Group.choices)
    actual = serializers.DecimalField(**MONEY)
    planned = serializers.DecimalField(**MONEY)
    percent_of_actual = serializers.DecimalField(**RATIO)
    percent_of_planned = serializers.DecimalField(**RATIO)


class PlannedActualSerializer(serializers.Serializer):
    planned = serializers.DecimalField(**MONEY)
    actual = serializers.DecimalField(**MONEY)


class DashboardSerializer(serializers.Serializer):
    month = serializers.DateField()
    bank_balance = BalanceSnapshotSerializer()
    emergency_fund_balance = BalanceSnapshotSerializer()
    savings = SavingsSerializer()
    expense_breakdown = ExpenseBreakdownItemSerializer(many=True)
    expense_totals = PlannedActualSerializer()
    income_totals = PlannedActualSerializer()
    credit_card_totals = PlannedActualSerializer()
