from datetime import date

import factory

from budget.models import Category, PlannedAmount
from users.tests.factories import UserFactory


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Category {n}")
    category_type = Category.CategoryType.EXPENSE
    group = Category.Group.NEEDS
    is_active = True


class PlannedAmountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PlannedAmount

    user = factory.SelfAttribute("category.user")
    category = factory.SubFactory(CategoryFactory)
    amount = "100.00"
    effective_from = factory.LazyFunction(lambda: date.today().replace(day=1))
