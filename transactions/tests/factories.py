from datetime import date

import factory

from budget.tests.factories import CategoryFactory
from transactions.models import InitialBalance, Transaction


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    user = factory.SelfAttribute("category.user")
    category = factory.SubFactory(CategoryFactory)
    amount = "100.00"
    date = factory.LazyFunction(date.today)
    description = factory.Sequence(lambda n: f"Transaction {n}")


class InitialBalanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InitialBalance

    user = factory.SubFactory("users.tests.factories.UserFactory")
    balance_type = InitialBalance.BalanceType.BANK
    amount = "1000.00"
    effective_month = factory.LazyFunction(lambda: date.today().replace(day=1))
