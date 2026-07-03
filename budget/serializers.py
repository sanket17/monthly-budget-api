from datetime import date

from rest_framework import serializers

from .models import Category, PlannedAmount
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


class PlannedAmountSerializer(serializers.ModelSerializer):
    """
    Serializer for setting a category's planned amount (BUDG-05/06).

    CRITICAL SECURITY (02-RESEARCH.md Pitfall 2 — the phase's core BOLA/IDOR
    risk): validate_category() is the ONLY defense against a user attaching
    a PlannedAmount to another user's Category via a crafted category id in
    the payload. UserScopedMixin does NOT protect against this — it only
    scopes the PlannedAmount object itself (read/list), never FK targets
    supplied on create. Do not remove this check.
    """

    class Meta:
        model = PlannedAmount
        fields = ("id", "category", "amount", "effective_from", "created_at")
        read_only_fields = ("id", "created_at")
        # D-03: no validation restricts effective_from to the current month
        # or later — users may intentionally set a future month's amount
        # early (e.g. set March's rent while still in January).

    def validate_category(self, value):
        request = self.context["request"]
        if value.user_id != request.user.id:
            raise serializers.ValidationError("Invalid category.")
        return value

    def create(self, validated_data):
        """
        D-08: if the category's most recent PlannedAmount row has
        effective_from still in the future relative to today (not yet
        effective for any queried month), update that row in place instead
        of appending a new one. Otherwise (no prior row, or the prior row
        has already taken effect), append a new row — an already-effective
        row is NEVER mutated (BUDG-08). Tie-break for identical
        effective_from values uses created_at descending (02-RESEARCH.md
        Pitfall 3).
        """
        category = validated_data["category"]
        current_month_start = date.today().replace(day=1)
        latest = (
            PlannedAmount.objects.filter(category=category)
            .order_by("-effective_from", "-created_at")
            .first()
        )
        if latest and latest.effective_from > current_month_start:
            latest.amount = validated_data["amount"]
            latest.effective_from = validated_data["effective_from"]
            latest.save(update_fields=["amount", "effective_from"])
            return latest
        return PlannedAmount.objects.create(**validated_data)
