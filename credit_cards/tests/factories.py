import factory

from credit_cards.models import CreditCard
from users.tests.factories import UserFactory


class CreditCardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CreditCard

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Card {n}")
    planned_amount = "5000.00"
    is_active = True
