"""
Recurring generation core tests (RECR-03/04).

Verification map:
  RECR-04: test_generates_transaction_and_is_idempotent_on_retry
  RECR-03: test_generate_for_user_with_no_active_entries
  D-03:    test_today_for_user_uses_provided_timezone
  D-21:    test_transaction_serializer_exposes_recurring_entry

Plan 06-03 extends this file to prove the generation algorithm Plan 06-01
built is correct under the hard cases: backfill depth, day clamping, the
creation-month boundary, per-entry failure isolation, the management
command, idempotency surviving manual deletion, real concurrent
double-generation, and edit semantics (D-01, D-07, D-08, D-09, D-10, D-11,
D-12, D-14, D-19).
"""

import calendar
from datetime import date, datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command

from budget.tests.factories import CategoryFactory
from recurring.models import RecurringEntry, RecurringGenerationLog
from recurring.services import generate_for_user, scheduled_date_for, today_for_user
from recurring.tests.factories import RecurringEntryFactory
from transactions.models import Transaction
from transactions.serializers import TransactionSerializer
from users.tests.factories import UserFactory


def _months_before(d: date, n: int) -> date:
    """
    Return the first-of-month date n calendar months before d's month,
    rolling the year back when the month underflows below January. Used to
    deterministically backdate created_at without a time-freezing library
    (none is installed in this project).
    """
    month_index = d.month - 1 - n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


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


@pytest.mark.django_db
class TestGenerationHardening:
    """
    Plan 06-03 Task 1: backfill depth, day-clamping, the creation-month
    boundary, per-entry failure isolation, and the management command
    (D-01, D-07, D-08, D-09, D-10, D-11).
    """

    def test_clamps_31st_in_short_month(self):
        year = date.today().year
        last_day = calendar.monthrange(year, 2)[1]

        result = scheduled_date_for(year, 2, 31)

        assert result.day == last_day
        assert result == date(year, 2, last_day)

    def test_backfills_missed_months_with_original_scheduled_dates(self):
        user = UserFactory()
        category = CategoryFactory(user=user, category_type="expense")
        entry = RecurringEntryFactory(user=user, category=category, day_of_month=1)

        current_month_start = date.today().replace(day=1)
        backdated_month = _months_before(current_month_start, 3)
        backdated_created_at = datetime(
            backdated_month.year, backdated_month.month, 1, tzinfo=dt_timezone.utc
        )
        RecurringEntry.all_objects.filter(pk=entry.pk).update(
            created_at=backdated_created_at
        )

        created = generate_for_user(user)

        assert len(created) == 4
        expected_months = [_months_before(current_month_start, n) for n in (3, 2, 1, 0)]
        created_dates = sorted(t.date for t in created)
        assert created_dates == expected_months
        assert (
            RecurringGenerationLog.objects.filter(recurring_entry=entry).count() == 4
        )

    def test_does_not_backfill_creation_month_if_day_already_passed(self):
        user = UserFactory()
        category = CategoryFactory(user=user, category_type="expense")
        entry = RecurringEntryFactory(user=user, category=category, day_of_month=1)

        current_month_start = date.today().replace(day=1)
        backdated_created_at = datetime(
            current_month_start.year,
            current_month_start.month,
            2,
            tzinfo=dt_timezone.utc,
        )
        RecurringEntry.all_objects.filter(pk=entry.pk).update(
            created_at=backdated_created_at
        )

        created = generate_for_user(user)

        assert created == []
        assert Transaction.objects.filter(recurring_entry=entry).count() == 0

    def test_continues_on_per_entry_failure(self, monkeypatch):
        user = UserFactory()
        category = CategoryFactory(user=user, category_type="expense")
        failing_entry = RecurringEntryFactory(
            user=user, category=category, day_of_month=date.today().day
        )
        healthy_entry = RecurringEntryFactory(
            user=user, category=category, day_of_month=date.today().day
        )

        import recurring.services as services

        real_generate_for_entry = services.generate_for_entry

        def flaky_generate_for_entry(entry, ceiling, today):
            if entry.id == failing_entry.id:
                raise RuntimeError("boom")
            return real_generate_for_entry(entry, ceiling, today)

        monkeypatch.setattr(services, "generate_for_entry", flaky_generate_for_entry)

        created = generate_for_user(user)

        assert len(created) == 1
        assert created[0].recurring_entry_id == healthy_entry.id

    def test_management_command_generates_for_all_users(self):
        user_a = UserFactory()
        category_a = CategoryFactory(user=user_a, category_type="expense")
        RecurringEntryFactory(
            user=user_a, category=category_a, day_of_month=date.today().day
        )
        user_b = UserFactory()
        category_b = CategoryFactory(user=user_b, category_type="expense")
        RecurringEntryFactory(
            user=user_b, category=category_b, day_of_month=date.today().day
        )

        call_command("generate_recurring_transactions")

        assert Transaction.objects.filter(user=user_a).count() == 1
        assert Transaction.objects.filter(user=user_b).count() == 1
