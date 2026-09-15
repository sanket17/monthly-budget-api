from datetime import date
from decimal import Decimal

from rest_framework import serializers

from .models import CreditCard, CreditCardEntry
from .services import get_actual_amount


class CreditCardSerializer(serializers.ModelSerializer):
    """
    Serializer for CreditCard CRUD (CARD-01/02) plus planned-vs-actual
    (CARD-05). actual_amount is read-only and computed for
    self.context["month"] (injected by CreditCardViewSet.get_serializer_context)
    via credit_cards.services.get_actual_amount — same pattern as
    budget/serializers.py CategorySerializer.get_planned_amount.
    planned_amount itself is a plain writable field — no carry-forward
    history (see CreditCard docstring).
    """

    actual_amount = serializers.SerializerMethodField()

    class Meta:
        model = CreditCard
        fields = ("id", "name", "planned_amount", "is_active", "actual_amount")
        read_only_fields = ("id", "is_active")  # mass-assignment defense

    def get_actual_amount(self, obj):
        month = self.context.get("month", date.today().replace(day=1))
        return get_actual_amount(obj.id, month)

    def validate_name(self, value):
        """
        Serializer-level backstop for the
        unique_active_credit_card_name_per_user UniqueConstraint
        (budget/serializers.py CategorySerializer.validate uses the same
        pattern): gives a fast, user-facing 400 instead of a raw
        IntegrityError. The DB constraint remains the actual guarantee.
        """
        request = self.context["request"]
        queryset = CreditCard.objects.filter(user=request.user, name=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "You already have an active credit card with this name."
            )
        return value


class CreditCardEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for CreditCardEntry CRUD (CARD-03/04).

    validate_card is the IDOR/BOLA defense against a user attaching an
    entry to another user's card via a crafted card id — UserScopedMixin
    only scopes the CreditCardEntry object itself, never FK targets
    supplied on create/update (same pattern as
    transactions/serializers.py TransactionSerializer.validate_category).
    The default queryset for `card` (CreditCard.objects, the active-only
    manager) already excludes soft-deleted cards, so a deleted card's id
    is rejected as "does not exist" before validate_card even runs.
    """

    class Meta:
        model = CreditCardEntry
        fields = ("id", "card", "amount", "date", "description", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_card(self, value):
        request = self.context["request"]
        if value.user_id != request.user.id:
            raise serializers.ValidationError("Invalid card.")
        return value

    def validate_amount(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
