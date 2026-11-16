"""
Builds the Postman collection + environments from the OpenAPI schema and the
examples in config/api_docs.py. Nothing here is hand-maintained per endpoint:
add an endpoint, regenerate (scripts/build_api_docs.py), done.
"""

import json
import re
import uuid

from . import api_docs

COLLECTION_NAME = "Personal Budget API"
NAMESPACE = uuid.UUID("6f1c2d3e-4a5b-4c6d-8e9f-0a1b2c3d4e5f")

PRODUCTION_URL = "https://api.paise-kuthe-gele.com"
LOCAL_URL = "http://localhost:8000"

# Query parameter -> example value used in the request URL.
QUERY_EXAMPLES = {
    "month": "2026-03",
    "page": "1",
    "page_size": "20",
    "card": "{{creditCardId}}",
}
# Optional query params that are enabled by default (shown in use).
QUERY_ENABLED = {("/api/dashboard/", "month"), ("/api/balance/", "month")}

SAMPLE_STRINGS = {
    "email": "asha@example.com",
    "first_name": "Asha",
    "last_name": "Patil",
    "timezone": "Asia/Kolkata",
    "name": "Groceries",
    "description": "Weekly groceries",
    "access": "<jwt access token>",
    "refresh": "<jwt refresh token>",
}
# Properties that are null in the typical response.
NULL_HINTS = {"next", "previous", "recurring_entry"}
SAMPLE_FORMATS = {
    "date": "2026-03-15",
    "date-time": "2026-03-15T09:30:00Z",
    "decimal": "2500.00",
    "email": "asha@example.com",
    "uri": "https://api.paise-kuthe-gele.com/api/transactions/?page=2",
}

# JavaScript helpers shared by the test scripts. `store()` writes to the active
# environment when one is selected, otherwise to collection variables, so the
# collection also works without an environment (baseUrl has a default).
_JS_STORE = (
    "const store = pm.environment.name ? pm.environment : pm.collectionVariables;"
)

AUTO_REFRESH_SCRIPT = [
    "// Refreshes the access token automatically when it is about to expire,",
    "// so you can keep sending requests for a whole working session.",
    "(function () {",
    "  if (/\\/api\\/auth\\//.test(pm.request.url.getPath())) return;",
    "  const refresh = pm.variables.get('refreshToken');",
    "  const access = pm.variables.get('accessToken');",
    "  if (!refresh) return;",
    "  let exp = 0;",
    "  try {",
    "    const payload = access.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');",
    "    exp = JSON.parse(atob(payload)).exp;",
    "  } catch (e) { /* no/invalid token: fall through and refresh */ }",
    "  if (exp - 30 > Date.now() / 1000) return;",
    f"  {_JS_STORE}",
    "  pm.sendRequest({",
    "    url: pm.variables.get('baseUrl') + '/api/auth/token/refresh/',",
    "    method: 'POST',",
    "    header: { 'Content-Type': 'application/json' },",
    "    body: { mode: 'raw', raw: JSON.stringify({ refresh: refresh }) }",
    "  }, function (err, res) {",
    "    if (err || res.code !== 200) return;",
    "    const body = res.json();",
    "    store.set('accessToken', body.access);",
    "    if (body.refresh) store.set('refreshToken', body.refresh);",
    "  });",
    "})();",
]

COLLECTION_DESCRIPTION = """\
REST API for the Personal Budget app. Base URL: `{{baseUrl}}`.

**Quick start**
1. Import this collection and one environment (Production or Local) and select it.
2. Run **Auth > Register**, then **Auth > Log in**. The tokens are saved
   automatically; every other request sends `Authorization: Bearer {{accessToken}}`.
3. Create a category, then a transaction. Create calls save the new id in
   `{{categoryId}}`, `{{transactionId}}`, ... so the next requests just work.

**Conventions**
- JSON in, JSON out: `Content-Type: application/json`, `Accept: application/json`.
- Money is a decimal **string** (`"450.00"`), never a float. Dates are
  `YYYY-MM-DD`; months are `YYYY-MM`.
- Access token lives 60 min; refresh token 7 days and **rotates** on every refresh.
- Errors: 400 `{"field": ["message"]}` (sometimes a bare array), 401/404/429
  `{"detail": "..."}`.

Full reference: the OpenAPI file (`docs/api/openapi.yaml`) and `/api/schema/swagger-ui/`.
"""


# ------------------------------------------------------------ sample values


def sample_value(schema, components, hint=""):
    """A plausible example value for a schema (used for saved responses)."""
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return sample_value(components[name], components, hint)
    if "example" in schema:
        return schema["example"]
    if "allOf" in schema:
        merged = {}
        for part in schema["allOf"]:
            value = sample_value(part, components, hint)
            if isinstance(value, dict):
                merged.update(value)
        return merged
    if "oneOf" in schema or "anyOf" in schema:
        return sample_value(
            (schema.get("oneOf") or schema["anyOf"])[0], components, hint
        )
    kind = schema.get("type")
    if hint in NULL_HINTS and schema.get("nullable", False):
        return None
    if "enum" in schema:
        return next((v for v in schema["enum"] if v), schema["enum"][0])
    if kind == "object" or "properties" in schema:
        out = {}
        for key, prop in schema.get("properties", {}).items():
            if prop.get("writeOnly"):
                continue
            out[key] = sample_value(prop, components, key)
        return out
    if kind == "array":
        return [sample_value(schema.get("items", {}), components, hint)]
    if kind == "integer":
        return 1
    if kind == "number":
        return 1.0
    if kind == "boolean":
        return True
    if kind == "string" or kind is None:
        if hint in SAMPLE_STRINGS:
            return SAMPLE_STRINGS[hint]
        return SAMPLE_FORMATS.get(schema.get("format"), "string")
    return None


def _json_schema_of(response):
    return (
        response.get("content", {}).get("application/json", {}).get("schema")
        if response
        else None
    )


def _dump(value):
    """Pretty JSON; Var placeholders become unquoted {{variables}}."""
    text = json.dumps(value, indent=2, ensure_ascii=False)
    return re.sub(r'"__VAR:(\w+)__"', r"{{\1}}", text)


# ---------------------------------------------------------------- scripts


def _test_script(path, method, status_codes, resource):
    ok = sorted(c for c in status_codes if c.startswith("2"))[0]
    lines = [
        f"pm.test('Status is {ok}', function () {{ pm.response.to.have.status({ok}); }});"
    ]
    if path == "/api/auth/login/":
        lines += [
            "const body = pm.response.json();",
            _JS_STORE,
            "store.set('accessToken', body.access);",
            "store.set('refreshToken', body.refresh);",
        ]
    elif path == "/api/auth/token/refresh/":
        lines += [
            "const body = pm.response.json();",
            _JS_STORE,
            "store.set('accessToken', body.access);",
            "// Rotation: the old refresh token is now revoked, keep the new one.",
            "if (body.refresh) store.set('refreshToken', body.refresh);",
        ]
    elif path == "/api/auth/logout/":
        lines += [
            _JS_STORE,
            "store.unset('accessToken');",
            "store.unset('refreshToken');",
        ]
    elif (
        method == "post"
        and resource in api_docs.ID_VARIABLES
        and path == f"/api/{resource}/"  # create only, not e.g. .../generate/
    ):
        variable = api_docs.ID_VARIABLES[resource]
        lines += [
            "const body = pm.response.json();",
            _JS_STORE,
            f"store.set('{variable}', body.id);",
        ]
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": lines}}]


# ---------------------------------------------------------------- requests


def _path_segments(path):
    out = []
    for part in path.strip("/").split("/"):
        if part == "{id}":
            out.append("{{%s}}" % ID_VAR_BY_PATH[path])
        else:
            out.append(part)
    out.append("")  # keep the trailing slash Django requires
    return out


ID_VAR_BY_PATH = {}


def _build_url(path, op):
    segments = _path_segments(path)
    query = []
    for param in op.get("parameters", []):
        if param.get("in") != "query":
            continue
        name = param["name"]
        query.append(
            {
                "key": name,
                "value": QUERY_EXAMPLES.get(name, ""),
                "description": param.get("description", ""),
                "disabled": (path, name) not in QUERY_ENABLED,
            }
        )
    raw = "{{baseUrl}}/" + "/".join(segments)
    enabled = [q for q in query if not q["disabled"]]
    if enabled:
        raw += "?" + "&".join(f"{q['key']}={q['value']}" for q in enabled)
    url = {"raw": raw, "host": ["{{baseUrl}}"], "path": segments}
    if query:
        url["query"] = query
    return url


def _headers(path, op):
    headers = [{"key": "Accept", "value": "application/json"}]
    if "requestBody" in op:
        headers.append({"key": "Content-Type", "value": "application/json"})
    if path not in api_docs.PUBLIC_PATHS:
        headers.append({"key": "Authorization", "value": "Bearer {{accessToken}}"})
    return headers


def _description(op):
    lines = [op.get("description", "").strip()]
    body = op.get("requestBody", {}).get("content", {}).get("application/json", {})
    if body:
        lines.append(
            "**Body:** JSON, see the example. Required fields are marked in the OpenAPI file."
        )
    codes = ", ".join(f"`{c}`" for c in op.get("responses", {}))
    lines.append(f"**Responses:** {codes}")
    return "\n\n".join(x for x in lines if x)


def _saved_responses(op, request, components, method, path):
    # Postman only needs the essentials of the originating request.
    request = {k: v for k, v in request.items() if k != "description"}
    examples = []
    for code, response in op.get("responses", {}).items():
        if code == "429":
            continue
        schema = _json_schema_of(response)
        if code == "204" or schema is None:
            body, label = "", ""
        else:
            body = _dump(sample_value(schema, components))
            label = "application/json"
        names = {
            "200": "Success",
            "201": "Created",
            "204": "Deleted",
            "400": "Validation error",
            "401": "Unauthorized",
            "404": "Not found",
        }
        examples.append(
            {
                "name": f"{code} {names.get(code, response.get('description', ''))}",
                "originalRequest": request,
                "status": names.get(code, "Response"),
                "code": int(code),
                "_postman_previewlanguage": "json" if label else "text",
                "header": (
                    [{"key": "Content-Type", "value": "application/json"}]
                    if label
                    else []
                ),
                "body": body,
            }
        )
    return examples


def _build_request(path, method, op, components):
    request = {
        "method": method.upper(),
        "header": _headers(path, op),
        "url": _build_url(path, op),
        "description": _description(op),
    }
    if path in api_docs.PUBLIC_PATHS:
        request["auth"] = {"type": "noauth"}
    example = api_docs.example_for(method, path)
    if example is not None and "requestBody" in op:
        request["body"] = {
            "mode": "raw",
            "raw": _dump(api_docs.resolve_vars(example, postman=True)),
            "options": {"raw": {"language": "json"}},
        }
    resource = api_docs.resource_of(path)
    item = {
        "name": op["summary"],
        "event": _test_script(path, method, list(op["responses"]), resource),
        "request": request,
    }
    item["response"] = _saved_responses(op, request, components, method, path)
    return item


_ORDER = {"get": 0, "post": 1, "put": 2, "patch": 3, "delete": 4}


def _op_sort_key(entry):
    path, method = entry
    detail = "{id}" in path
    # list, create, then detail operations; PATCH .../reactivate/ and
    # POST .../generate/ after plain CRUD.
    extra = 1 if path.rstrip("/").split("/")[-1] in ("reactivate", "generate") else 0
    return (api_docs.PATH_ORDER.get(path, 0), extra, detail, _ORDER[method], path)


def build_collection(schema):
    components = schema["components"]["schemas"]
    for path in schema["paths"]:
        resource = api_docs.resource_of(path)
        if resource in api_docs.ID_VARIABLES:
            ID_VAR_BY_PATH[path] = api_docs.ID_VARIABLES[resource]

    by_tag = {slug: [] for slug, _, _ in api_docs.TAGS}
    for path, item in schema["paths"].items():
        for method in api_docs.HTTP_METHODS:
            op = item.get(method)
            if op is None:
                continue
            by_tag[op["tags"][0]].append((path, method))

    folders = []
    for slug, title, description in api_docs.TAGS:
        entries = sorted(by_tag[slug], key=_op_sort_key)
        if not entries:
            continue
        folders.append(
            {
                "name": title,
                "description": description,
                "item": [
                    _build_request(
                        path, method, schema["paths"][path][method], components
                    )
                    for path, method in entries
                ],
            }
        )

    return {
        "info": {
            "_postman_id": str(uuid.uuid5(NAMESPACE, COLLECTION_NAME)),
            "name": COLLECTION_NAME,
            "description": COLLECTION_DESCRIPTION,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "event": [
            {
                "listen": "prerequest",
                "script": {"type": "text/javascript", "exec": AUTO_REFRESH_SCRIPT},
            }
        ],
        "variable": [{"key": "baseUrl", "value": PRODUCTION_URL, "type": "string"}],
        "item": folders,
    }


def build_environment(name, base_url):
    values = [
        {"key": "baseUrl", "value": base_url, "type": "default", "enabled": True},
        {"key": "accessToken", "value": "", "type": "secret", "enabled": True},
        {"key": "refreshToken", "value": "", "type": "secret", "enabled": True},
    ]
    values += [
        {"key": variable, "value": "", "type": "default", "enabled": True}
        for variable in api_docs.ID_VARIABLES.values()
    ]
    return {
        "id": str(uuid.uuid5(NAMESPACE, name)),
        "name": name,
        "values": values,
        "_postman_variable_scope": "environment",
    }


def build_postman_files(schema):
    """filename -> JSON text for everything under docs/api/postman/."""
    files = {
        "Personal-Budget-API.postman_collection.json": build_collection(schema),
        "production.postman_environment.json": build_environment(
            "Personal Budget - Production", PRODUCTION_URL
        ),
        "local.postman_environment.json": build_environment(
            "Personal Budget - Local", LOCAL_URL
        ),
    }
    return {
        name: json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
        for name, doc in files.items()
    }
