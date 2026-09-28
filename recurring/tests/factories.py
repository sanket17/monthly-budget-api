import factory

from recurring.models import RecurringEntry


class RecurringEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RecurringEntry

    # Linking user to category.user (not an independent SubFactory) prevents
    # accidentally creating a factory instance whose user and category.user
    # mismatch, which would trip validate_category in any API-level test
    # built on this factory — mirrors
    # transactions/tests/factories.py::TransactionFactory's safer pattern.
    user = factory.SelfAttribute("category.user")
    category = factory.SubFactory("budget.tests.factories.CategoryFactory")
    amount = "100.00"
    description = factory.Sequence(lambda n: f"Recurring entry {n}")
    day_of_month = 1
    is_active = True
