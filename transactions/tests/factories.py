from datetime import date

import factory

from budget.tests.factories import CategoryFactory
from transactions.models import Transaction


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    user = factory.SelfAttribute("category.user")
    category = factory.SubFactory(CategoryFactory)
    amount = "100.00"
    date = factory.LazyFunction(date.today)
    description = factory.Sequence(lambda n: f"Transaction {n}")
