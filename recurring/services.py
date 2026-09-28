"""
Recurring entry generation (RECR-03/04): the shared function both the
manual-generate endpoint (Plan 06-02) and the cron management command call
to turn due RecurringEntry rows into real Transaction rows.

Idempotency (D-19) is enforced by RecurringGenerationLog's DB
UniqueConstraint(recurring_entry, period) inside transaction.atomic(), with
an IntegrityError catch — never an app-level existence pre-check. This
survives a manually deleted Transaction: deleting the generated Transaction
does not remove the log row, so a re-run never recreates it.

Per-user "today" is always resolved via the owning user's own IANA
timezone (D-03) — never the server clock or a global default.
"""

import calendar
import logging
from datetime import date, datetime

from django.db import IntegrityError, transaction
from zoneinfo import ZoneInfo

from transactions.models import Transaction

from .models import RecurringGenerationLog

logger = logging.getLogger(__name__)


def _next_month(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def scheduled_date_for(year: int, month: int, day_of_month: int) -> date:
    """
    D-01: when the target month has fewer days than day_of_month (e.g. 31
    in February), the occurrence fires on that month's actual last day
    instead of being skipped.
    """
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, min(day_of_month, last_day))


def today_for_user(user) -> date:
    """
    D-03: per-user "today" resolved via the owning user's own IANA
    timezone — never the server clock or a global default.
    """
    return datetime.now(ZoneInfo(user.timezone)).date()


def _generate_one(entry, scheduled_date: date, period: date):
    """
    Creates the Transaction and its RecurringGenerationLog row inside a
    single atomic block. An IntegrityError on the log's UniqueConstraint
    means a concurrent run already generated this (entry, period) — that
    is not an error, so we return None (D-19).
    """
    try:
        with transaction.atomic():
            created = Transaction.objects.create(
                user=entry.user,
                category=entry.category,
                amount=entry.amount,
                date=scheduled_date,
                description=entry.description,
                recurring_entry=entry,
            )
            RecurringGenerationLog.objects.create(
                recurring_entry=entry, period=period
            )
    except IntegrityError:
        return None
    return created


def generate_for_entry(entry, ceiling: date, today: date):
    """
    Walks every calendar month from the later of the entry's creation
    month or the month after its last successful generation (D-08), up to
    ceiling (inclusive), generating one Transaction per due month.

    D-10: a scheduled date that had already strictly passed before the
    entry existed is skipped for the creation month only — a scheduled
    date equal to the creation date DOES generate (inclusive boundary).
    D-09: the generated Transaction is always dated with its original
    scheduled date, never the date generation actually ran.
    """
    creation_date_local = entry.created_at.astimezone(ZoneInfo(entry.user.timezone)).date()
    creation_month = creation_date_local.replace(day=1)
    last_log = entry.generation_log.order_by("-period").first()
    if last_log is None:
        start = creation_month
    else:
        start = max(creation_month, _next_month(last_log.period))

    created_transactions = []
    current = start
    while current <= ceiling:
        scheduled = scheduled_date_for(current.year, current.month, entry.day_of_month)
        if current == creation_month and scheduled < creation_date_local:
            current = _next_month(current)
            continue
        if scheduled > today:
            break
        result = _generate_one(entry, scheduled, current)
        if result is not None:
            created_transactions.append(result)
        current = _next_month(current)

    return created_transactions


def generate_for_user(user, upto_month: date | None = None):
    """
    Generates due Transactions for every active RecurringEntry belonging
    to user. If generation raises for one entry, the failure is logged and
    every other entry still gets processed (D-07) — a single bad entry
    never aborts the whole run.
    """
    today = today_for_user(user)
    ceiling = upto_month or today.replace(day=1)

    created_transactions = []
    for entry in user.recurring_entries.filter(is_active=True):
        try:
            created_transactions.extend(generate_for_entry(entry, ceiling, today))
        except Exception:
            logger.exception(
                "Recurring generation failed for entry %s (user %s)",
                entry.id,
                user.id,
            )
    return created_transactions
