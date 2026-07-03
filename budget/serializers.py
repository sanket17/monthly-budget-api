from datetime import date

from rest_framework import serializers

from .models import Category
from .services import get_effective_amount


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category CRUD (BUDG-01..04).

    planned_amount is read-only and computed for self.context["month"]
    (injected by CategoryViewSet.get_serializer_context) via
    budget.services.get_effective_amount — carry-forward resolution
    (BUDG-07).
    """

    planned_amount = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "category_type", "group", "is_active", "planned_amount")
        read_only_fields = (
            "id",
            "is_active",
        )  # mass-assignment defense — client never sets these

    def get_planned_amount(self, obj):
        month = self.context.get("month", date.today().replace(day=1))
        return get_effective_amount(obj.id, month)

    def validate(self, data):
        """
        Serializer-level backstop for the group_required_iff_expense
        CheckConstraint (Don't Hand-Roll table, 02-RESEARCH.md): gives a
        fast, user-facing 400 instead of a raw IntegrityError. The DB
        constraint (budget/models.py) remains the actual guarantee.
        """
        category_type = data.get(
            "category_type", getattr(self.instance, "category_type", None)
        )
        group = data.get("group", getattr(self.instance, "group", None))
        if category_type == Category.CategoryType.EXPENSE and not group:
            raise serializers.ValidationError(
                {"group": "Group is required for expense categories."}
            )
        # D-04: income categories are name-only — no group of any kind.
        if category_type == Category.CategoryType.INCOME and group:
            raise serializers.ValidationError(
                {"group": "Income categories must not have a group."}
            )
        return data
