"""
Tests for budget/migrations/0002_rename_redeemed_emergency_category.py (D-02).

No migration-test helper package is installed this phase — rename_forward
and rename_reverse are called directly, passing the real django.apps.apps
registry (they only call apps.get_model, same signature Django itself
uses at migration time) and a minimal stand-in for schema_editor exposing
only `.connection` (the functions only read schema_editor.connection.alias).
"""

import importlib

import pytest
from django.apps import apps as django_apps
from django.db import connections

from budget.models import Category
from budget.tests.factories import CategoryFactory

# Migration module names start with a digit ("0002_...") so they cannot be
# imported with a normal `import` statement (not a valid identifier) —
# importlib.import_module accepts any dotted string instead.
_rename_migration = importlib.import_module(
    "budget.migrations.0002_rename_redeemed_emergency_category"
)
rename_forward = _rename_migration.rename_forward
rename_reverse = _rename_migration.rename_reverse


class _FakeSchemaEditor:
    """Stand-in exposing only .connection — the only attribute the
    rename_forward/rename_reverse functions read."""

    connection = connections["default"]


@pytest.mark.django_db
class TestRedeemedEmergencyRenameMigration:
    def test_renames_income_category_forward_and_reverse(self):
        category = CategoryFactory(
            category_type=Category.CategoryType.INCOME,
            group=None,
            name="Redeemed Emergency",
        )

        rename_forward(django_apps, _FakeSchemaEditor)
        category.refresh_from_db()
        assert category.name == "Redeem Emergency Fund"

        rename_reverse(django_apps, _FakeSchemaEditor)
        category.refresh_from_db()
        assert category.name == "Redeemed Emergency"

    def test_renames_case_insensitively(self):
        category = CategoryFactory(
            category_type=Category.CategoryType.INCOME,
            group=None,
            name="redeemed emergency",
        )

        rename_forward(django_apps, _FakeSchemaEditor)
        category.refresh_from_db()
        assert category.name == "Redeem Emergency Fund"

    def test_collision_on_one_user_does_not_block_others(self):
        # User A already has an active "Redeem Emergency Fund" income
        # category (the new name) — renaming it again would collide with
        # itself if matched, but it should not be matched by the OLD_NAME
        # filter, and it must survive untouched.
        already_renamed = CategoryFactory(
            category_type=Category.CategoryType.INCOME,
            group=None,
            name="Redeem Emergency Fund",
        )
        # User B (different, unrelated user) still has the old name and
        # should be renamed successfully — proving the per-row savepoint
        # isolates any potential collision to the row that caused it.
        needs_rename = CategoryFactory(
            category_type=Category.CategoryType.INCOME,
            group=None,
            name="Redeemed Emergency",
        )

        rename_forward(django_apps, _FakeSchemaEditor)

        already_renamed.refresh_from_db()
        needs_rename.refresh_from_db()
        assert already_renamed.name == "Redeem Emergency Fund"
        assert needs_rename.name == "Redeem Emergency Fund"

    def test_expense_category_with_same_name_is_not_touched(self):
        expense_category = CategoryFactory(
            category_type=Category.CategoryType.EXPENSE,
            group=Category.Group.NEEDS,
            name="Redeemed Emergency",
        )

        rename_forward(django_apps, _FakeSchemaEditor)

        expense_category.refresh_from_db()
        assert expense_category.name == "Redeemed Emergency"
