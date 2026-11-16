"""
Full CRUD + soft-delete + reactivate + IDOR + generate-endpoint test suite
for RecurringEntry (RECR-01/02/03/05, D-12/13/14/16/17/18, D-22..26).

Mirrors budget/tests/test_categories.py's class/fixture structure.
"""

import threading
from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.urls import reverse
from rest_framework.test import APIClient

from budget.tests.factories import CategoryFactory
from recurring.models import RecurringEntry
from recurring.tests.factories import RecurringEntryFactory
from recurring.views import RecurringEntryViewSet
from users.tests.factories import UserFactory


@pytest.mark.django_db
class TestRecurringEntryCRUD:
    """RECR-01/02: create and edit expense/income recurring entries."""

    def test_create_expense_entry(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense", group="needs")
        payload = {
            "category": category.id,
            "amount": "50.00",
            "description": "Netflix",
            "day_of_month": 5,
        }
        response = client.post(reverse("recurring-entry-list"), payload)
        assert response.status_code == 201
        assert response.data["description"] == "Netflix"
        assert RecurringEntry.objects.get(id=response.data["id"]).user == user

    def test_create_income_entry(self, authenticated_client):
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="income", group=None)
        payload = {
            "category": category.id,
            "amount": "5000.00",
            "description": "Salary",
            "day_of_month": 1,
        }
        response = client.post(reverse("recurring-entry-list"), payload)
        assert response.status_code == 201
        assert response.data["category"] == category.id

    def test_edit_amount_and_description(self, authenticated_client):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        response = client.patch(
            reverse("recurring-entry-detail", args=[entry.id]),
            {"amount": "75.00", "description": "Updated"},
        )
        assert response.status_code == 200
        assert response.data["amount"] == "75.00"
        assert response.data["description"] == "Updated"

    def test_create_entry_with_other_users_category_returns_400(
        self, authenticated_client
    ):
        client, _ = authenticated_client
        other_users_category = CategoryFactory(category_type="expense", group="needs")
        payload = {
            "category": other_users_category.id,
            "amount": "50.00",
            "description": "IDOR attempt",
            "day_of_month": 5,
        }
        response = client.post(reverse("recurring-entry-list"), payload)
        assert response.status_code == 400


@pytest.mark.django_db
class TestRecurringEntrySoftDeleteAndReactivate:
    """RECR-05, D-13/D-17: soft-delete + reactivate semantics."""

    def test_soft_delete(self, authenticated_client):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        response = client.delete(reverse("recurring-entry-detail", args=[entry.id]))
        assert response.status_code == 204
        entry.refresh_from_db()
        assert entry.is_active is False
        list_response = client.get(reverse("recurring-entry-list"))
        assert entry.id not in [e["id"] for e in list_response.data]

    def test_delete_twice_is_idempotent_404_on_second_call(self, authenticated_client):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        url = reverse("recurring-entry-detail", args=[entry.id])
        first = client.delete(url)
        assert first.status_code == 204
        second = client.delete(url)
        assert second.status_code == 404

    def test_reactivate_own_entry(self, authenticated_client):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user, is_active=False)
        url = reverse("recurring-entry-reactivate", args=[entry.id])
        response = client.patch(url)
        assert response.status_code == 200
        entry.refresh_from_db()
        assert entry.is_active is True

    def test_reactivate_rejected_when_category_was_soft_deleted(
        self, authenticated_client
    ):
        """G4/D-15: an active entry may not point at a deleted category."""
        client, user = authenticated_client
        category = CategoryFactory(user=user, category_type="expense")
        entry = RecurringEntryFactory(user=user, category=category)
        client.delete(reverse("recurring-entry-detail", args=[entry.id]))
        client.delete(reverse("category-detail", args=[category.id]))

        response = client.patch(reverse("recurring-entry-reactivate", args=[entry.id]))

        assert response.status_code == 400
        entry.refresh_from_db()
        assert entry.is_active is False

    def test_reactivate_other_users_entry_returns_404(self, authenticated_client):
        client, _ = authenticated_client
        user_a = UserFactory()
        entry_a = RecurringEntryFactory(category__user=user_a, is_active=False)
        url = reverse("recurring-entry-reactivate", args=[entry_a.id])
        response = client.patch(url)
        assert response.status_code == 404
        entry_a.refresh_from_db()
        assert entry_a.is_active is False


@pytest.mark.django_db
class TestRecurringEntryCategoryValidation:
    """D-16/D-18: category validation on edit."""

    def test_change_category_to_inactive_category_returns_400(
        self, authenticated_client
    ):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        inactive_category = CategoryFactory(
            user=user, category_type="expense", group="needs", is_active=False
        )
        response = client.patch(
            reverse("recurring-entry-detail", args=[entry.id]),
            {"category": inactive_category.id},
        )
        assert response.status_code == 400

    def test_change_category_to_emergency_fund_category_succeeds(
        self, authenticated_client
    ):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        emergency_fund = CategoryFactory(
            user=user,
            category_type="expense",
            group="needs",
            name="Emergency Fund",
        )
        response = client.patch(
            reverse("recurring-entry-detail", args=[entry.id]),
            {"category": emergency_fund.id},
        )
        assert response.status_code == 200
        assert response.data["category"] == emergency_fund.id

    def test_change_category_to_redeem_emergency_fund_category_succeeds(
        self, authenticated_client
    ):
        client, user = authenticated_client
        entry = RecurringEntryFactory(category__user=user)
        redeem_emergency_fund = CategoryFactory(
            user=user,
            category_type="income",
            group=None,
            name="Redeem Emergency Fund",
        )
        response = client.patch(
            reverse("recurring-entry-detail", args=[entry.id]),
            {"category": redeem_emergency_fund.id},
        )
        assert response.status_code == 200
        assert response.data["category"] == redeem_emergency_fund.id


@pytest.mark.django_db
class TestCrossUserIsolation:
    """Security: UserScopedMixin — User B cannot access User A's entries."""

    def test_cross_user_cannot_access_other_entry(self, authenticated_client):
        client, _ = authenticated_client
        user_a = UserFactory()
        entry_a = RecurringEntryFactory(category__user=user_a)
        response = client.get(reverse("recurring-entry-detail", args=[entry_a.id]))
        assert response.status_code == 404

    def test_cross_user_cannot_delete_other_entry(self, authenticated_client):
        client, _ = authenticated_client
        user_a = UserFactory()
        entry_a = RecurringEntryFactory(category__user=user_a)
        response = client.delete(reverse("recurring-entry-detail", args=[entry_a.id]))
        assert response.status_code == 404
        entry_a.refresh_from_db()
        assert entry_a.is_active is True


@pytest.mark.django_db
class TestGenerateEndpoint:
    """D-22..26: on-demand generate-now endpoint."""

    def test_generate_endpoint_creates_transactions_for_current_month(
        self, authenticated_client
    ):
        client, user = authenticated_client
        RecurringEntryFactory(category__user=user, day_of_month=date.today().day)

        response = client.post(reverse("recurring-generate"))

        assert response.status_code == 200
        assert len(response.data) == 1
        assert "amount" in response.data[0]
        assert "date" in response.data[0]

    def test_generate_endpoint_is_idempotent_within_month(self, authenticated_client):
        client, user = authenticated_client
        RecurringEntryFactory(category__user=user, day_of_month=date.today().day)

        first = client.post(reverse("recurring-generate"))
        assert first.status_code == 200
        assert len(first.data) == 1

        second = client.post(reverse("recurring-generate"))
        assert second.status_code == 200
        assert second.data == []

    def test_generate_endpoint_only_affects_caller(self, authenticated_client):
        client, _ = authenticated_client
        other_user = UserFactory()
        RecurringEntryFactory(category__user=other_user, day_of_month=date.today().day)

        response = client.post(reverse("recurring-generate"))

        assert response.status_code == 200
        assert response.data == []

    def test_generate_endpoint_requires_authentication(self, api_client):
        response = api_client.post(reverse("recurring-generate"))
        assert response.status_code == 401


@pytest.mark.django_db(transaction=True)
class TestConcurrentEditAndDelete:
    """
    UAT 06 #3 (06-02-PLAN must_have, verification: backstop): a PATCH and a
    DELETE hitting the same recurring entry at the same instant must never
    produce a server error or a corrupted row. Outcome is last-write-wins
    on a single row, so either order is acceptable; the invariants below
    hold for both. Real threads + real commits (transaction=True) against
    Postgres; a Barrier lines both requests up to maximise overlap, and
    the scenario repeats to sample different interleavings.
    """

    ITERATIONS = 10

    def _race(self, user, entry):
        url = reverse("recurring-entry-detail", args=[entry.id])
        barrier = threading.Barrier(2)
        statuses = {}
        errors = []

        def call(name, method, payload):
            try:
                client = APIClient()
                client.force_authenticate(user=user)
                barrier.wait(timeout=10)
                response = getattr(client, method)(url, payload, format="json")
                statuses[name] = response.status_code
            except Exception as exc:  # pragma: no cover - surfaced via errors list
                errors.append(exc)
            finally:
                connection.close()

        threads = [
            threading.Thread(
                target=call, args=("patch", "patch", {"amount": "250.00"})
            ),
            threading.Thread(target=call, args=("delete", "delete", None)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return statuses, errors

    def test_concurrent_patch_and_delete_leave_row_consistent(self):
        user = UserFactory()
        category = CategoryFactory(user=user, category_type="expense")

        for _ in range(self.ITERATIONS):
            entry = RecurringEntryFactory(
                user=user, category=category, amount="100.00", day_of_month=7
            )

            statuses, errors = self._race(user, entry)

            assert errors == []
            # DELETE is a soft delete: always succeeds, idempotent.
            assert statuses["delete"] == 204
            # PATCH either won the race (200) or ran after the soft delete,
            # when the active-only queryset no longer sees the row (404).
            assert statuses["patch"] in (200, 404)

            # Exactly one row, never hard-deleted, never duplicated.
            rows = RecurringEntry.all_objects.filter(pk=entry.pk)
            assert rows.count() == 1
            final = rows.get()
            # Untouched fields are intact; amount is cleanly old or new.
            assert final.user_id == user.id
            assert final.category_id == category.id
            assert final.day_of_month == 7
            assert final.amount in (Decimal("100.00"), Decimal("250.00"))
            if statuses["patch"] == 404:
                assert final.amount == Decimal("100.00")
                assert final.is_active is False

    def test_delete_during_patch_is_not_resurrected(self, monkeypatch):
        """
        Lost-update regression: a PATCH that already loaded the entry must
        not undo a DELETE (soft delete) that lands before the PATCH saves.
        ModelSerializer.update() re-saves the whole row, so without a row
        lock the stale is_active=True would overwrite the soft delete.

        Deterministic interleave: the PATCH is paused right after
        get_object() (inside perform_update) until the DELETE has been
        issued. With the row locked, the DELETE blocks until the PATCH
        commits, so the pause times out and the DELETE is applied last.
        Without the lock the DELETE finishes inside the pause window and
        the PATCH then clobbers it.
        """
        user = UserFactory()
        category = CategoryFactory(user=user, category_type="expense")
        entry = RecurringEntryFactory(
            user=user, category=category, amount="100.00", day_of_month=7
        )
        url = reverse("recurring-entry-detail", args=[entry.id])

        patch_loaded = threading.Event()
        delete_done = threading.Event()
        original_perform_update = RecurringEntryViewSet.perform_update

        def paused_perform_update(self, serializer):
            patch_loaded.set()
            delete_done.wait(timeout=1.5)
            return original_perform_update(self, serializer)

        monkeypatch.setattr(
            RecurringEntryViewSet, "perform_update", paused_perform_update
        )

        statuses = {}
        errors = []

        def do_patch():
            try:
                client = APIClient()
                client.force_authenticate(user=user)
                statuses["patch"] = client.patch(
                    url, {"amount": "250.00"}, format="json"
                ).status_code
            except Exception as exc:  # pragma: no cover - surfaced via errors list
                errors.append(exc)
            finally:
                connection.close()

        def do_delete():
            try:
                assert patch_loaded.wait(timeout=10)
                client = APIClient()
                client.force_authenticate(user=user)
                statuses["delete"] = client.delete(url).status_code
            except Exception as exc:  # pragma: no cover - surfaced via errors list
                errors.append(exc)
            finally:
                delete_done.set()
                connection.close()

        threads = [
            threading.Thread(target=do_patch),
            threading.Thread(target=do_delete),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert statuses == {"patch": 200, "delete": 204}
        final = RecurringEntry.all_objects.get(pk=entry.pk)
        assert final.is_active is False
        assert final.amount == Decimal("250.00")


@pytest.mark.django_db(transaction=True)
class TestConcurrentReactivateAndCategoryDelete:
    """
    G4 race: DELETE category checks "no active entries" while a concurrent
    reactivate flips an entry active. Both serialize on the category row
    lock, so the invariant "no active entry points at a deleted category"
    must hold for every interleaving.
    """

    ITERATIONS = 15

    def test_never_leaves_active_entry_on_deleted_category(self):
        user = UserFactory()
        for _ in range(self.ITERATIONS):
            category = CategoryFactory(user=user, category_type="expense")
            entry = RecurringEntryFactory(
                user=user, category=category, is_active=False
            )
            barrier = threading.Barrier(2)
            statuses = {}
            errors = []

            def call(name, method, url):
                try:
                    client = APIClient()
                    client.force_authenticate(user=user)
                    barrier.wait(timeout=10)
                    statuses[name] = getattr(client, method)(url).status_code
                except Exception as exc:  # pragma: no cover
                    errors.append(exc)
                finally:
                    connection.close()

            threads = [
                threading.Thread(
                    target=call,
                    args=(
                        "reactivate",
                        "patch",
                        reverse("recurring-entry-reactivate", args=[entry.id]),
                    ),
                ),
                threading.Thread(
                    target=call,
                    args=("delete", "delete", reverse("category-detail", args=[category.id])),
                ),
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert errors == []
            category.refresh_from_db()
            entry.refresh_from_db()
            assert not (entry.is_active and not category.is_active), statuses
            # Exactly one side wins: reactivate (200) XOR category delete (204).
            assert sorted(statuses.values()) in ([200, 400], [204, 400]), statuses
