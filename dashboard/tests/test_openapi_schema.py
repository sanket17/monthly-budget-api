"""
G5: the OpenAPI schema documents the plain-APIView endpoints and stays
warning-free, and the schema-only response serializers cannot silently
drift away from the real payloads.
"""

from datetime import date

import pytest
import yaml
from django.core.management import call_command
from django.urls import reverse

from dashboard.serializers import DashboardSerializer
from dashboard.services import get_dashboard
from transactions.serializers import BalanceSummarySerializer
from transactions.tests.factories import InitialBalanceFactory


@pytest.fixture(scope="module")
def schema(tmp_path_factory):
    out = tmp_path_factory.mktemp("schema") / "schema.yml"
    # --fail-on-warn: any unresolved serializer/type hint is a test failure.
    call_command("spectacular", "--fail-on-warn", "--file", str(out))
    return yaml.safe_load(out.read_text())


def _op(schema, path, method):
    return schema["paths"][path][method]


def _json_response_ref(op, status="200"):
    return op["responses"][status]["content"]["application/json"]["schema"]


class TestSchemaCoversApiViews:
    def test_balance_documents_month_param_and_response(self, schema):
        op = _op(schema, "/api/balance/", "get")
        assert "month" in [p["name"] for p in op["parameters"]]
        assert _json_response_ref(op)["$ref"].endswith("/BalanceSummary")

    def test_dashboard_documents_month_param_and_response(self, schema):
        op = _op(schema, "/api/dashboard/", "get")
        assert "month" in [p["name"] for p in op["parameters"]]
        assert _json_response_ref(op)["$ref"].endswith("/Dashboard")

    def test_generate_documents_transaction_list_response(self, schema):
        op = _op(schema, "/api/recurring-entries/generate/", "post")
        body = _json_response_ref(op, "200")
        assert body["type"] == "array"
        assert body["items"]["$ref"].endswith("/Transaction")
        assert "requestBody" not in op

    def test_entry_list_documents_card_and_month_filters(self, schema):
        op = _op(schema, "/api/credit-card-entries/", "get")
        assert {"month", "card"} <= {p["name"] for p in op["parameters"]}

    def test_method_fields_are_typed_as_decimal_strings(self, schema):
        planned = schema["components"]["schemas"]["Category"]["properties"][
            "planned_amount"
        ]
        actual = schema["components"]["schemas"]["CreditCard"]["properties"][
            "actual_amount"
        ]
        assert planned["type"] == actual["type"] == "string"
        assert planned["format"] == actual["format"] == "decimal"


@pytest.mark.django_db
class TestResponseSerializersMatchPayloads:
    MONTH = date(2026, 3, 1)

    def test_dashboard_payload_has_exactly_the_documented_fields(self, user_factory):
        user = user_factory()
        InitialBalanceFactory(user=user, effective_month=self.MONTH)
        payload = get_dashboard(user.id, self.MONTH)

        serializer = DashboardSerializer(payload)

        assert set(DashboardSerializer().fields) == set(payload)
        assert set(serializer.data["savings"]) == set(payload["savings"])
        assert set(serializer.data["expense_breakdown"][0]) == set(
            payload["expense_breakdown"][0]
        )

    def test_balance_endpoint_matches_documented_fields(self, authenticated_client):
        client, user = authenticated_client
        InitialBalanceFactory(user=user, effective_month=self.MONTH)

        response = client.get(reverse("balance-summary"), {"month": "2026-03"})

        assert set(response.data) == set(BalanceSummarySerializer().fields)
        assert set(response.data["bank_balance"]) == {"opening", "closing"}
