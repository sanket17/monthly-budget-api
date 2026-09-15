from decimal import Decimal

from rest_framework import serializers

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for Transaction CRUD (TXNS-01..04).

    validate_category is the IDOR/BOLA defense against a user attaching a
    transaction to another user's category via a crafted category id in
    the payload — UserScopedMixin only scopes the Transaction object
    itself, never FK targets supplied on create/update (same pattern as
    budget/serializers.py PlannedAmountSerializer.validate_category).
    """

    class Meta:
        model = Transaction
        fields = ("id", "category", "amount", "date", "description", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_category(self, value):
        request = self.context["request"]
        if value.user_id != request.user.id:
            raise serializers.ValidationError("Invalid category.")
        return value

    def validate_amount(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
