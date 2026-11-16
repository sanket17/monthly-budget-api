"""
The published API docs (docs/api/) must describe the API as it really is.

- structure tests pin the conventions mobile developers rely on;
- the contract test replays the Postman collection against the live API: every
  example body must be accepted, every captured id must chain, and each response
  must have exactly the keys the saved example documents;
- the drift test fails when the committed files are stale
  (fix: python scripts/build_api_docs.py);
- the script test runs the collection's JavaScript under Node with a mocked pm.
"""

import base64
import json
import re
import shutil
import subprocess
import time

import pytest
from rest_framework.test import APIClient

from config import api_docs, postman
from config.docs_build import DOCS_DIR, build_all, generate_schema

pytestmark = pytest.mark.filterwarnings("ignore")

OPS = [
    (path, method)
    for path, item in generate_schema()["paths"].items()
    for method in api_docs.HTTP_METHODS
    if method in item
]


@pytest.fixture(scope="module")
def schema():
    return generate_schema()


@pytest.fixture(scope="module")
def collection(schema):
    return postman.build_collection(schema)


def _template_path(request):
    """Collection URL path -> OpenAPI path template ('{{categoryId}}' -> '{id}')."""
    parts = ["{id}" if p.startswith("{{") else p for p in request["url"]["path"]]
    return "/" + "/".join(parts)


def _requests(collection):
    for folder in collection["item"]:
        for item in folder["item"]:
            yield folder["name"], item


# ------------------------------------------------------------------ schema


class TestSchemaConventions:
    def test_servers_and_tags(self, schema):
        assert [s["url"] for s in schema["servers"]][0].startswith("https://")
        assert {t["name"] for t in schema["tags"]} == set(api_docs.TAG_TITLES)

    @pytest.mark.parametrize("path,method", OPS)
    def test_every_operation_is_documented(self, schema, path, method):
        op = schema["paths"][path][method]
        assert op["summary"] and not op["summary"].startswith(method.upper())
        assert op["tags"][0] in api_docs.TAG_TITLES
        if path in api_docs.PUBLIC_PATHS:
            assert op["security"] == []
        else:
            assert op["security"] == [{"jwtAuth": []}]
            assert "401" in op["responses"]
        if "{id}" in path:
            assert "404" in op["responses"]
        if "requestBody" in op:
            assert "400" in op["responses"]

    @pytest.mark.parametrize(
        "path,method",
        [(p, m) for p, m in OPS if m in ("post", "put", "patch")],
    )
    def test_every_request_body_has_an_example(self, schema, path, method):
        op = schema["paths"][path][method]
        if "requestBody" not in op:
            return
        for media in op["requestBody"]["content"].values():
            assert "example" in media, f"{method.upper()} {path} has no example body"

    def test_no_internal_text_is_published(self):
        files = build_all()
        for name, text in files.items():
            match = api_docs.INTERNAL_MARKER.search(text)
            assert match is None, f"{name} leaks internal text: {match.group(0)!r}"

    def test_reactivate_has_no_request_body(self, schema):
        op = schema["paths"]["/api/recurring-entries/{id}/reactivate/"]["patch"]
        assert "requestBody" not in op


# -------------------------------------------------------------- collection


class TestCollectionStructure:
    def test_covers_every_operation_exactly_once(self, schema, collection):
        documented = sorted(
            (item["request"]["method"], _template_path(item["request"]))
            for _, item in _requests(collection)
        )
        expected = sorted((m.upper(), p) for p, m in OPS)
        assert documented == expected

    def test_headers(self, collection):
        for _, item in _requests(collection):
            request = item["request"]
            headers = {h["key"]: h["value"] for h in request["header"]}
            path = _template_path(request)
            assert headers["Accept"] == "application/json"
            if "body" in request:
                assert headers["Content-Type"] == "application/json"
            if path in api_docs.PUBLIC_PATHS:
                assert "Authorization" not in headers
                assert request["auth"] == {"type": "noauth"}
            else:
                assert headers["Authorization"] == "Bearer {{accessToken}}"

    def test_bodies_are_valid_json_once_variables_are_filled(self, collection):
        for _, item in _requests(collection):
            body = item["request"].get("body")
            if body:
                json.loads(re.sub(r"{{(\w+)}}", "1", body["raw"]))

    def test_environments_define_every_variable_used(self, collection):
        used = set(re.findall(r"{{(\w+)}}", json.dumps(collection["item"])))
        for name in ("production", "local"):
            env = json.loads(build_all()[f"postman/{name}.postman_environment.json"])
            defined = {v["key"] for v in env["values"]}
            assert used <= defined, used - defined
        secrets = {v["key"] for v in env["values"] if v["type"] == "secret"}
        assert secrets == {"accessToken", "refreshToken"}


# ----------------------------------------------------------------- contract

SUBSTITUTION = re.compile(r"{{(\w+)}}")


def _fill(text, variables):
    return SUBSTITUTION.sub(lambda m: str(variables[m.group(1)]), text)


def _expected_status(item):
    return int(
        re.search(r"Status is (\d+)", item["event"][0]["script"]["exec"][0]).group(1)
    )


def _documented_body(item, status):
    for saved in item["response"]:
        if saved["code"] == status and saved["body"]:
            return json.loads(saved["body"])
    return None


def _shape_keys(value):
    if isinstance(value, dict):
        return set(value)
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return set(value[0])
    return None


@pytest.mark.django_db
class TestCollectionAgainstTheLiveApi:
    def _send(self, client, item, variables):
        request = item["request"]
        path = "/" + "/".join(_fill(p, variables) for p in request["url"]["path"])
        query = [
            f"{q['key']}={_fill(q['value'], variables)}"
            for q in request["url"].get("query", [])
            if not q.get("disabled")
        ]
        if query:
            path += "?" + "&".join(query)
        extra = {}
        for header in request["header"]:
            if header["key"] == "Authorization":
                extra["HTTP_AUTHORIZATION"] = _fill(header["value"], variables)
        body = request.get("body")
        kwargs = {"content_type": "application/json"} if body else {}
        data = _fill(body["raw"], variables) if body else ""
        return client.generic(request["method"], path, data, **kwargs, **extra)

    def _apply_scripts(self, item, response, variables):
        """What the item's Postman test script does with the response."""
        script = "\n".join(item["event"][0]["script"]["exec"])
        body = response.json() if response.content else {}
        if "store.set('accessToken'" in script:
            variables["accessToken"] = body["access"]
            if "refresh" in body:
                variables["refreshToken"] = body["refresh"]
        for match in re.finditer(r"store\.set\('(\w+Id)', body\.id\)", script):
            variables[match.group(1)] = body["id"]

    def test_replaying_the_collection_works_end_to_end(self, collection):
        client = APIClient()
        variables = {"baseUrl": ""}
        items = [(f, i) for f, i in _requests(collection)]
        first_pass = [
            (f, i)
            for f, i in items
            if not i["name"].startswith("Delete")
            and not i["name"].startswith("Log out")
        ]
        deletes = [(f, i) for f, i in items if i["name"].startswith("Delete")]
        logout = [(f, i) for f, i in items if i["name"].startswith("Log out")]
        ordered = first_pass + list(reversed(deletes)) + logout

        for folder, item in ordered:
            response = self._send(client, item, variables)
            want = _expected_status(item)
            assert response.status_code == want, (
                f"{item['name']}: expected {want}, got {response.status_code} "
                f"{getattr(response, 'content', b'')[:300]!r}"
            )
            self._apply_scripts(item, response, variables)

            documented = _documented_body(item, want)
            if documented is not None:
                actual = response.json()
                expected_keys, actual_keys = _shape_keys(documented), _shape_keys(
                    actual
                )
                if actual_keys is not None and expected_keys is not None:
                    assert actual_keys == expected_keys, (
                        f"{item['name']}: documented response keys "
                        f"{sorted(expected_keys)} != actual {sorted(actual_keys)}"
                    )

    def test_documented_errors_match_reality(self, collection):
        client = APIClient()
        bad_login = client.post(
            "/api/auth/login/", {"email": "no@one.com", "password": "x"}, format="json"
        )
        assert bad_login.status_code == 401 and "detail" in bad_login.json()
        assert client.get("/api/categories/").status_code == 401
        bad_register = client.post("/api/auth/register/", {"email": "x"}, format="json")
        assert bad_register.status_code == 400
        assert set(bad_register.json()) >= {"email", "password"}


# -------------------------------------------------------------------- drift


def test_committed_docs_are_up_to_date():
    stale = []
    for relative, text in build_all().items():
        target = DOCS_DIR / relative
        if not target.exists() or target.read_text() != text:
            stale.append(relative)
    assert (
        not stale
    ), f"stale API docs: {stale}. Run: python scripts/build_api_docs.py and commit."


# ------------------------------------------------------------------ scripts

needs_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node not installed"
)

HARNESS = """
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const calls = { set: {}, unset: [], sent: [] };
const store = {
  name: input.environmentName,
  set: (k, v) => { calls.set[k] = v; },
  unset: (k) => { calls.unset.push(k); },
};
const vars = input.vars || {};
const pm = {
  environment: input.environmentName ? store : { name: undefined },
  collectionVariables: input.environmentName ? { set() {}, unset() {} } : store,
  variables: { get: (k) => vars[k] },
  request: { url: { getPath: () => input.path || '/api/transactions/' } },
  response: {
    json: () => input.response,
    to: { have: { status: () => {} } },
  },
  sendRequest: (opts, cb) => {
    calls.sent.push(opts);
    cb(null, { code: 200, json: () => input.refreshResponse });
  },
};
pm.environment.name = input.environmentName;
global.pm = pm;
global.pm.test = () => {};
new Function('pm', 'atob', input.script)(pm, (s) => Buffer.from(s, 'base64').toString());
console.log(JSON.stringify(calls));
"""


def _run_script(lines, **context):
    out = subprocess.run(
        ["node", "-e", HARNESS],
        input=json.dumps({"script": "\n".join(lines), **context}),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def _jwt(exp):
    def b64(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    return f"{b64({'alg': 'none'})}.{b64({'exp': exp})}.sig"


def _find(collection, name):
    return next(i for _, i in _requests(collection) if i["name"] == name)


@needs_node
class TestPostmanScripts:
    def test_login_stores_both_tokens(self, collection):
        item = _find(collection, "Log in")
        calls = _run_script(
            item["event"][0]["script"]["exec"],
            environmentName="Prod",
            response={"access": "A1", "refresh": "R1"},
        )
        assert calls["set"] == {"accessToken": "A1", "refreshToken": "R1"}

    def test_works_without_an_environment(self, collection):
        item = _find(collection, "Log in")
        calls = _run_script(
            item["event"][0]["script"]["exec"],
            environmentName=None,
            response={"access": "A1", "refresh": "R1"},
        )
        assert calls["set"] == {"accessToken": "A1", "refreshToken": "R1"}

    def test_refresh_keeps_the_rotated_refresh_token(self, collection):
        item = _find(collection, "Refresh access token")
        calls = _run_script(
            item["event"][0]["script"]["exec"],
            environmentName="Prod",
            response={"access": "A2", "refresh": "R2"},
        )
        assert calls["set"] == {"accessToken": "A2", "refreshToken": "R2"}

    def test_logout_clears_tokens(self, collection):
        item = _find(collection, "Log out (revoke refresh token)")
        calls = _run_script(
            item["event"][0]["script"]["exec"], environmentName="Prod", response={}
        )
        assert calls["unset"] == ["accessToken", "refreshToken"]

    def test_create_saves_the_new_id(self, collection):
        item = _find(collection, "Create transaction")
        calls = _run_script(
            item["event"][0]["script"]["exec"],
            environmentName="Prod",
            response={"id": 42},
        )
        assert calls["set"] == {"transactionId": 42}

    def test_collection_prerequest_refreshes_only_when_needed(self, collection):
        script = collection["event"][0]["script"]["exec"]
        refresh_response = {"access": "NEW", "refresh": "NEWR"}
        now = int(time.time())

        def run(**kw):
            return _run_script(
                script,
                environmentName="Prod",
                refreshResponse=refresh_response,
                **kw,
            )

        expired = run(
            vars={
                "accessToken": _jwt(now - 60),
                "refreshToken": "R",
                "baseUrl": "https://x",
            }
        )
        assert len(expired["sent"]) == 1
        assert expired["sent"][0]["url"] == "https://x/api/auth/token/refresh/"
        assert json.loads(expired["sent"][0]["body"]["raw"]) == {"refresh": "R"}
        assert expired["set"] == {"accessToken": "NEW", "refreshToken": "NEWR"}

        fresh = run(
            vars={
                "accessToken": _jwt(now + 3600),
                "refreshToken": "R",
                "baseUrl": "https://x",
            }
        )
        assert fresh["sent"] == []

        no_refresh = run(vars={"accessToken": _jwt(now - 60), "baseUrl": "https://x"})
        assert no_refresh["sent"] == []

        auth_call = run(
            path="/api/auth/login/",
            vars={
                "accessToken": _jwt(now - 60),
                "refreshToken": "R",
                "baseUrl": "https://x",
            },
        )
        assert auth_call["sent"] == []

        garbage = run(
            vars={
                "accessToken": "not-a-jwt",
                "refreshToken": "R",
                "baseUrl": "https://x",
            }
        )
        assert len(garbage["sent"]) == 1
