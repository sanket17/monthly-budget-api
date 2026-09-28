import itertools

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from recurring.services import generate_for_user

User = get_user_model()


class Command(BaseCommand):
    """
    Cron entry point (RECR-03/04): generates due recurring Transactions for
    every user with at least one active RecurringEntry. Calls the same
    shared generate_for_user() function used by the manual-generate
    endpoint (Plan 06-02) — no separate generation logic lives here.

    Users are grouped by timezone (order_by + itertools.groupby) purely for
    readability of a potential future per-timezone batching optimization;
    generate_for_user() itself resolves "today" independently per user via
    CustomUser.timezone (D-03), so grouping has no effect on correctness.
    """

    help = "Generate due Transactions for every user's active recurring entries."

    def handle(self, *args, **options):
        users = User.objects.filter(
            recurring_entries__is_active=True
        ).distinct().order_by("timezone")

        total_created = 0
        for _timezone, group in itertools.groupby(users, key=lambda u: u.timezone):
            for user in group:
                created = generate_for_user(user)
                total_created += len(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {total_created} recurring transaction(s)."
            )
        )
