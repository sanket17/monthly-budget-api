from decimal import Decimal

from rest_framework import serializers

from .models import RecurringEntry


class RecurringEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for RecurringEntry CRUD (RECR-01/02).

    validate_category is the IDOR/BOLA defense against a user attaching a
    recurring entry to another user's category via a crafted category id
    in the payload — copied verbatim from
    transactions/serializers.py::TransactionSerializer.validate_category.
    """

    class Meta:
        model = RecurringEntry
        fields = (
            "id",
            "category",
            "amount",
            "description",
            "day_of_month",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "is_active", "created_at")

    def validate_category(self, value):
        request = self.context["request"]
        if value.user_id != request.user.id:
            raise serializers.ValidationError("Invalid category.")
        return value

    def validate_amount(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
