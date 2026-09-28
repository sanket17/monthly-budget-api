"""
Recurring generation core tests (RECR-03/04).

Verification map:
  RECR-04: test_generates_transaction_and_is_idempotent_on_retry
  RECR-03: test_generate_for_user_with_no_active_entries
  D-03:    test_today_for_user_uses_provided_timezone
  D-21:    test_transaction_serializer_exposes_recurring_entry
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from budget.tests.factories import CategoryFactory
from recurring.models import RecurringGenerationLog
from recurring.services import generate_for_user, today_for_user
from recurring.tests.factories import RecurringEntryFactory
from transactions.models import Transaction
from transactions.serializers import TransactionSerializer
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestGenerationCore:
    def test_generates_transaction_and_is_idempotent_on_retry(self):
        user = UserFactory()
        category = CategoryFactory(user=user, category_type="expense")
        entry = RecurringEntryFactory(
            user=user, category=category, day_of_month=date.today().day
        )

        created = generate_for_user(user)

        assert len(created) == 1
        assert created[0].recurring_entry_id == entry.id
        assert (
            RecurringGenerationLog.objects.filter(recurring_entry=entry).count() == 1
        )

        created_again = generate_for_user(user)

        assert created_again == []
        assert Transaction.objects.filter(recurring_entry=entry).count() == 1

    def test_generate_for_user_with_no_active_entries(self):
        user = UserFactory()

        created = generate_for_user(user)

        assert created == []

    def test_today_for_user_uses_provided_timezone(self):
        user = UserFactory(timezone="Pacific/Kiritimati")

        result = today_for_user(user)

        expected = datetime.now(ZoneInfo("Pacific/Kiritimati")).date()
        assert result == expected

    def test_transaction_serializer_exposes_recurring_entry(self):
        user = UserFactory()
        category = CategoryFactory(user=user, category_type="expense")
        entry = RecurringEntryFactory(
            user=user, category=category, day_of_month=date.today().day
        )

        created = generate_for_user(user)
        created_transaction = created[0]

        data = TransactionSerializer(created_transaction).data

        assert data["recurring_entry"] == entry.id
