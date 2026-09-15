from datetime import date

import factory

from credit_cards.models import CreditCard, CreditCardEntry
from users.tests.factories import UserFactory


class CreditCardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CreditCard

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Card {n}")
    planned_amount = "5000.00"
    is_active = True


class CreditCardEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CreditCardEntry

    user = factory.SelfAttribute("card.user")
    card = factory.SubFactory(CreditCardFactory)
    amount = "100.00"
    date = factory.LazyFunction(date.today)
    description = factory.Sequence(lambda n: f"Entry {n}")
