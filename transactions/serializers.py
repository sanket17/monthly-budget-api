from decimal import Decimal

from rest_framework import serializers

from .models import InitialBalance, Transaction


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
        fields = (
            "id",
            "category",
            "amount",
            "date",
            "description",
            "recurring_entry",
            "created_at",
        )
        read_only_fields = ("id", "recurring_entry", "created_at")

    def validate_category(self, value):
        request = self.context["request"]
        if value.user_id != request.user.id:
            raise serializers.ValidationError("Invalid category.")
        return value

    def validate_amount(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class InitialBalanceSerializer(serializers.ModelSerializer):
    """
    Serializer for setting a user's bank or emergency-fund initial balance
    (BALN-01/03). One row per (user, balance_type) — see InitialBalance
    docstring. create() upserts via update_or_create instead of relying on
    the DB UniqueConstraint to raise IntegrityError on a second POST.
    """

    class Meta:
        model = InitialBalance
        fields = ("id", "balance_type", "amount", "effective_month", "created_at")
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        obj, _ = InitialBalance.objects.update_or_create(
            user=validated_data["user"],
            balance_type=validated_data["balance_type"],
            defaults={
                "amount": validated_data["amount"],
                "effective_month": validated_data["effective_month"],
            },
        )
        return obj
