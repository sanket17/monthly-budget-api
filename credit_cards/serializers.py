from rest_framework import serializers

from .models import CreditCard


class CreditCardSerializer(serializers.ModelSerializer):
    """
    Serializer for CreditCard CRUD (CARD-01/02). planned_amount is a plain
    writable field — no carry-forward history (see CreditCard docstring).
    """

    class Meta:
        model = CreditCard
        fields = ("id", "name", "planned_amount", "is_active")
        read_only_fields = ("id", "is_active")  # mass-assignment defense

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
