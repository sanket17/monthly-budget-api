"""
Single source of truth for the human-facing API documentation.

Everything a mobile developer needs beyond what drf-spectacular infers from
the code lives here: friendly operation names, request-body examples, behaviour
notes, which endpoints are public, and the documented error shapes.

`enhance_schema` is registered as a drf-spectacular postprocessing hook
(config/settings/base.py), so the live schema at /api/schema/ and the committed
docs/api/openapi.yaml both carry this. config/postman.py builds the Postman
collection from the same data. tests in config/tests/test_api_docs.py execute
every example against the real API, so the docs cannot drift from the code.
"""

import re

HTTP_METHODS = ("get", "put", "post", "patch", "delete")

# Developer-only text that must never reach the published docs: planning
# requirement ids (TXNS-01, D-12, T-06-05, WR-01...), file references, phases.
INTERNAL_MARKER = re.compile(
    r"\b(?:[A-Z]{2,5}-\d{2}|D-\d{2}|T-\d{2}-\d{2})\b|CLAUDE\.md|\b\w+\.py\b|\bPhase \d"
)


def has_internal_text(text):
    return bool(text and INTERNAL_MARKER.search(text))


SERVERS = [
    {"url": "https://api.paise-kuthe-gele.com", "description": "Production"},
    {"url": "http://localhost:8000", "description": "Local development"},
]

# Endpoints that need no Authorization header.
PUBLIC_PATHS = {
    "/api/auth/register/",
    "/api/auth/login/",
    "/api/auth/token/refresh/",
    "/api/auth/logout/",
}

# Order requests are listed in the collection, for folders that are a workflow
# rather than CRUD (a new user registers before logging in).
PATH_ORDER = {
    "/api/auth/register/": 0,
    "/api/auth/login/": 1,
    "/api/auth/token/refresh/": 2,
    "/api/auth/logout/": 3,
}

# Throttled with the strict "auth" scope (5 requests/minute per client IP).
STRICT_THROTTLE_PATHS = {"/api/auth/register/", "/api/auth/login/"}

# Folder order and descriptions (also the Postman folder order).
TAGS = [
    ("auth", "Auth", "Register, log in, refresh and revoke JWT tokens."),
    ("users", "Users", "The signed-in user's own profile."),
    (
        "categories",
        "Categories",
        "Expense and income categories. 49 defaults are created at registration.",
    ),
    (
        "planned-amounts",
        "Planned amounts",
        "Monthly budget per category. Append-only; carries forward month to month.",
    ),
    (
        "transactions",
        "Transactions",
        "Individual income and expense records, listed one calendar month at a time.",
    ),
    (
        "initial-balances",
        "Initial balances",
        "Starting bank / emergency-fund balance that the running balances grow from.",
    ),
    ("balance", "Balance", "Opening and closing balances for a month."),
    (
        "credit-cards",
        "Credit cards",
        "Credit cards with a planned monthly amount and the actual spend per month.",
    ),
    (
        "credit-card-entries",
        "Credit card entries",
        "Individual credit-card spends. They never change the bank balance.",
    ),
    (
        "recurring-entries",
        "Recurring entries",
        "Monthly auto-generated transactions (rent, salary, subscriptions).",
    ),
    ("dashboard", "Dashboard", "One call that composes everything for a month."),
]
TAG_TITLES = {slug: title for slug, title, _ in TAGS}

# Postman variable that holds the id captured from each resource's create call.
ID_VARIABLES = {
    "categories": "categoryId",
    "planned-amounts": "plannedAmountId",
    "transactions": "transactionId",
    "initial-balances": "initialBalanceId",
    "credit-cards": "creditCardId",
    "credit-card-entries": "creditCardEntryId",
    "recurring-entries": "recurringEntryId",
}


class Var:
    """
    A value that is a literal in the OpenAPI example (`default`) but a Postman
    variable (`{{name}}`) in the collection, so requests chain together.
    """

    def __init__(self, name, default):
        self.name = name
        self.default = default


CATEGORY_ID = Var("categoryId", 1)
CARD_ID = Var("creditCardId", 1)

# (METHOD, path) -> request body example. PUT reuses the full POST body.
_CATEGORY = {"name": "Groceries", "category_type": "expense", "group": "needs"}
_CARD_ENTRY = {
    "card": CARD_ID,
    "amount": "1299.00",
    "date": "2026-03-12",
    "description": "Online shopping",
}
_RECURRING = {
    "category": CATEGORY_ID,
    "amount": "15000.00",
    "description": "House rent",
    "day_of_month": 1,
}
_TRANSACTION = {
    "category": CATEGORY_ID,
    "amount": "450.00",
    "date": "2026-03-15",
    "description": "Weekly groceries",
}
_CREDIT_CARD = {"name": "HDFC Millennia", "planned_amount": "15000.00"}

EXAMPLES = {
    ("POST", "/api/auth/register/"): {
        "email": "asha@example.com",
        "password": "S3cure-pass!",
        "first_name": "Asha",
        "last_name": "Patil",
        "timezone": "Asia/Kolkata",
    },
    ("POST", "/api/auth/login/"): {
        "email": "asha@example.com",
        "password": "S3cure-pass!",
    },
    ("POST", "/api/auth/token/refresh/"): {"refresh": Var("refreshToken", "<refresh>")},
    ("POST", "/api/auth/logout/"): {"refresh": Var("refreshToken", "<refresh>")},
    ("PATCH", "/api/users/me/"): {
        "first_name": "Asha",
        "last_name": "Patil",
        "timezone": "Asia/Kolkata",
    },
    ("POST", "/api/categories/"): _CATEGORY,
    ("PUT", "/api/categories/{id}/"): _CATEGORY,
    ("PATCH", "/api/categories/{id}/"): {"name": "Groceries & Staples"},
    ("POST", "/api/planned-amounts/"): {
        "category": CATEGORY_ID,
        "amount": "12000.00",
        "effective_from": "2026-03-01",
    },
    ("POST", "/api/transactions/"): _TRANSACTION,
    ("PUT", "/api/transactions/{id}/"): _TRANSACTION,
    ("PATCH", "/api/transactions/{id}/"): {"amount": "475.00"},
    ("POST", "/api/initial-balances/"): {
        "balance_type": "bank",
        "amount": "50000.00",
        "effective_month": "2026-03-01",
    },
    ("POST", "/api/credit-cards/"): _CREDIT_CARD,
    ("PUT", "/api/credit-cards/{id}/"): _CREDIT_CARD,
    ("PATCH", "/api/credit-cards/{id}/"): {"planned_amount": "20000.00"},
    ("POST", "/api/credit-card-entries/"): _CARD_ENTRY,
    ("PUT", "/api/credit-card-entries/{id}/"): _CARD_ENTRY,
    ("PATCH", "/api/credit-card-entries/{id}/"): {"amount": "999.00"},
    ("POST", "/api/recurring-entries/"): _RECURRING,
    ("PUT", "/api/recurring-entries/{id}/"): _RECURRING,
    ("PATCH", "/api/recurring-entries/{id}/"): {"day_of_month": 5},
}

# Friendly names for operations that are not plain resource CRUD.
SPECIAL_SUMMARIES = {
    ("POST", "/api/auth/register/"): "Register",
    ("POST", "/api/auth/login/"): "Log in",
    ("POST", "/api/auth/token/refresh/"): "Refresh access token",
    ("POST", "/api/auth/logout/"): "Log out (revoke refresh token)",
    ("GET", "/api/users/me/"): "Get my profile",
    ("PATCH", "/api/users/me/"): "Update my profile",
    ("GET", "/api/balance/"): "Get bank and emergency-fund balance for a month",
    ("GET", "/api/dashboard/"): "Get dashboard for a month",
    ("PATCH", "/api/recurring-entries/{id}/reactivate/"): "Reactivate recurring entry",
    ("POST", "/api/recurring-entries/generate/"): "Generate this month's transactions",
}

# resource path segment -> (singular, plural)
RESOURCE_NAMES = {
    "categories": ("category", "categories"),
    "planned-amounts": ("planned amount", "planned amounts"),
    "transactions": ("transaction", "transactions"),
    "initial-balances": ("initial balance", "initial balances"),
    "credit-cards": ("credit card", "credit cards"),
    "credit-card-entries": ("credit card entry", "credit card entries"),
    "recurring-entries": ("recurring entry", "recurring entries"),
}

# Behaviour a client developer must know. Verified against the code/tests.
NOTES = {
    ("POST", "/api/auth/register/"): (
        "Creates the account and seeds 49 default categories. `timezone` must be an "
        'IANA name (e.g. `Asia/Kolkata`, default `UTC`) and decides what "today" '
        "means for recurring entries. A taken email returns a generic 400 on purpose. "
        "Limited to 5 requests/minute per IP."
    ),
    ("POST", "/api/auth/login/"): (
        "Returns a short-lived `access` token (60 minutes) and a `refresh` token "
        "(7 days). Send `Authorization: Bearer <access>` on every other request. "
        "Limited to 5 requests/minute per IP."
    ),
    ("POST", "/api/auth/token/refresh/"): (
        "Refresh tokens **rotate**: the response contains a NEW `refresh` token and "
        "the one you sent is revoked. Always store the new one. A 401 here means the "
        "user must log in again."
    ),
    ("POST", "/api/auth/logout/"): (
        "Revokes the refresh token. Discard both tokens on the device afterwards. "
        "No Authorization header is needed."
    ),
    ("GET", "/api/categories/"): (
        "Returns a plain JSON array (not paginated) of the user's active categories. "
        "`planned_amount` is the planned amount in effect for `?month=` (default: "
        "current month)."
    ),
    ("POST", "/api/categories/"): (
        "Expense categories require `group` (`needs`, `wants`, `investment`, "
        "`other`); income categories must NOT have a group. Names are unique among "
        "the user's active categories of the same type."
    ),
    ("PATCH", "/api/categories/{id}/"): (
        "`category_type` cannot be changed once the category has transactions, "
        "planned amounts or recurring entries (400). Renaming and moving between "
        "groups is always allowed."
    ),
    ("DELETE", "/api/categories/{id}/"): (
        "Soft delete: history is kept. Returns 400 (body is a JSON array with one "
        "message) while an active recurring entry uses the category."
    ),
    ("POST", "/api/planned-amounts/"): (
        "Append-only: there is no PUT/PATCH/DELETE. POST a new amount with the month "
        "it takes effect from (`effective_from`); it applies to that month and "
        "carries forward until the next one."
    ),
    ("GET", "/api/transactions/"): (
        "Paginated and limited to ONE calendar month: `?month=YYYY-MM` (default: "
        "current month). Use `page` / `page_size` (default 20, max 100). Newest first. "
        "Response is `{count, next, previous, results}`."
    ),
    ("POST", "/api/transactions/"): (
        "Whether it is income or expense comes from the chosen category. `amount` "
        "must be greater than 0. The category must belong to the user. "
        "`recurring_entry` is set by the server for generated transactions."
    ),
    ("GET", "/api/transactions/{id}/"): (
        "Detail, update and delete work for a transaction in ANY month; the month "
        "window applies only to the list."
    ),
    ("POST", "/api/initial-balances/"): (
        "One row per `balance_type` (`bank` or `emergency_fund`): posting again "
        "replaces it. `effective_month` is normalised to the 1st of the month. "
        "There is no PUT/PATCH/DELETE."
    ),
    ("GET", "/api/balance/"): (
        "`opening`/`closing` are null when no initial balance is set or the month is "
        "before it. Bank balance counts transactions only, never credit-card entries."
    ),
    ("GET", "/api/credit-cards/"): (
        "Plain array of active cards. `actual_amount` is the spend on the card in "
        "`?month=` (default: current month)."
    ),
    ("DELETE", "/api/credit-cards/{id}/"): ("Soft delete: its entries are kept."),
    ("GET", "/api/credit-card-entries/"): (
        "Paginated and limited to one month (`?month=`, default current), optionally "
        "to one card (`?card=<id>`). Response is `{count, next, previous, results}`."
    ),
    ("POST", "/api/credit-card-entries/"): (
        "`card` must be one of the user's active cards. Entries never affect the "
        "bank balance."
    ),
    ("POST", "/api/recurring-entries/"): (
        "`day_of_month` is 1-31; in shorter months it runs on the last day. The "
        "category must be active and the user's own. The server generates the "
        "transactions (see Generate)."
    ),
    ("DELETE", "/api/recurring-entries/{id}/"): (
        "Soft delete: already generated transactions stay."
    ),
    ("PATCH", "/api/recurring-entries/{id}/reactivate/"): (
        "Takes no body. Returns 400 if the entry's category was deleted."
    ),
    ("POST", "/api/recurring-entries/generate/"): (
        "Creates any due transactions up to today (in the user's timezone) for the "
        "current month. Idempotent; returns only the ones created (often `[]`)."
    ),
    ("GET", "/api/dashboard/"): (
        "Savings, expense breakdown by group, planned-vs-actual totals and balances "
        "for the month. Amounts are decimal strings; percentages are unrounded "
        "decimal strings and null when the denominator is zero."
    ),
}


def resource_of(path):
    """'/api/categories/{id}/' -> 'categories' (None for non-resource paths)."""
    parts = [p for p in path.split("/") if p]
    return parts[1] if len(parts) > 1 and parts[1] in RESOURCE_NAMES else None


def summary_for(method, path):
    key = (method.upper(), path)
    if key in SPECIAL_SUMMARIES:
        return SPECIAL_SUMMARIES[key]
    resource = resource_of(path)
    if resource is None:
        return f"{method.upper()} {path}"
    singular, plural = RESOURCE_NAMES[resource]
    detail = "{id}" in path
    verbs = {
        ("GET", False): f"List {plural}",
        ("POST", False): f"Create {singular}",
        ("GET", True): f"Get {singular}",
        ("PUT", True): f"Replace {singular} (PUT)",
        ("PATCH", True): f"Update {singular} (PATCH)",
        ("DELETE", True): f"Delete {singular}",
    }
    return verbs[(method.upper(), detail)]


def example_for(method, path):
    return EXAMPLES.get((method.upper(), path))


def resolve_vars(value, *, postman):
    """Replace Var markers: literal default for OpenAPI, '{{name}}' for Postman."""
    if isinstance(value, Var):
        if not postman:
            return value.default
        # Strings stay quoted ("{{refreshToken}}"); numbers (ids) become a bare
        # {{categoryId}} - _dump() in config/postman.py unquotes this marker.
        if isinstance(value.default, str):
            return "{{%s}}" % value.name
        return f"__VAR:{value.name}__"
    if isinstance(value, dict):
        return {k: resolve_vars(v, postman=postman) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_vars(v, postman=postman) for v in value]
    return value


# ---------------------------------------------------------------- error docs

ERROR_SCHEMAS = {
    "ErrorDetail": {
        "type": "object",
        "description": "Used for 401, 403, 404 and 429 responses.",
        "properties": {
            "detail": {"type": "string", "example": "Not found."},
            "code": {
                "type": "string",
                "description": "Present on token errors, e.g. `token_not_valid`.",
                "example": "token_not_valid",
            },
        },
        "required": ["detail"],
    },
    "ValidationErrors": {
        "type": "object",
        "description": (
            "400 body. Keys are field names; each value is a list of messages "
            "(sometimes a single string, e.g. for an invalid `month` query). "
            "A few 400s return a bare JSON array of messages instead, so a client "
            "should accept all three shapes."
        ),
        "additionalProperties": {
            "oneOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
            ]
        },
        "example": {"amount": ["Amount must be greater than zero."]},
    },
}


def _error_response(description, schema_name):
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
            }
        },
    }


def _add_errors(op, method, path):
    responses = op.setdefault("responses", {})
    has_body = "requestBody" in op
    has_query = any(p.get("in") == "query" for p in op.get("parameters", []))
    blocked_delete = method == "delete" and path == "/api/categories/{id}/"
    if has_body or has_query or blocked_delete:
        responses.setdefault(
            "400", _error_response("Validation error.", "ValidationErrors")
        )
    if path in PUBLIC_PATHS:
        if path != "/api/auth/register/":
            responses.setdefault(
                "401",
                _error_response(
                    "Wrong credentials, or the token is invalid/expired.", "ErrorDetail"
                ),
            )
    else:
        responses.setdefault(
            "401",
            _error_response(
                "Missing, invalid or expired access token. Refresh it, or log in "
                "again if refresh also fails.",
                "ErrorDetail",
            ),
        )
    if "{id}" in path:
        responses.setdefault(
            "404", _error_response("Not found (or not the user's).", "ErrorDetail")
        )
    if path in STRICT_THROTTLE_PATHS:
        responses.setdefault(
            "429", _error_response("Too many requests; retry later.", "ErrorDetail")
        )


def enhance_schema(result, generator, request, public):
    """drf-spectacular postprocessing hook."""
    result["servers"] = SERVERS
    result["tags"] = [
        {"name": slug, "x-displayName": title, "description": description}
        for slug, title, description in TAGS
    ]
    schemas = result.setdefault("components", {}).setdefault("schemas", {})
    for schema in schemas.values():
        if has_internal_text(schema.get("description")):
            del schema["description"]
    schemas.update(ERROR_SCHEMAS)

    for path, item in result["paths"].items():
        for method in HTTP_METHODS:
            op = item.get(method)
            if op is None:
                continue
            op["summary"] = summary_for(method, path)
            op["security"] = [] if path in PUBLIC_PATHS else [{"jwtAuth": []}]
            note = NOTES.get((method.upper(), path))
            if (
                resource_of(path) is not None
                or path in PUBLIC_PATHS
                or has_internal_text(op.get("description"))
            ):
                # ViewSet docstrings are developer notes (internal requirement
                # ids, file references): never publish them. Use curated notes.
                op["description"] = note or ""
            elif note:
                base = op.get("description", "").strip()
                op["description"] = f"{base}\n\n{note}".strip()
            _add_errors(op, method, path)
            example = example_for(method, path)
            if example is not None and "requestBody" in op:
                literal = resolve_vars(example, postman=False)
                for media in op["requestBody"]["content"].values():
                    media["example"] = literal
    return result
