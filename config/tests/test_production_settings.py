"""
Loads config.settings.production in a fresh interpreter (settings are
import-time constants, and the test run itself uses the development module)
and asserts the hardening a real deployment depends on.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

PROBE = """
import json
from django.conf import settings
print(json.dumps({
    "debug": settings.DEBUG,
    "proxy_header": settings.SECURE_PROXY_SSL_HEADER,
    "session_secure": settings.SESSION_COOKIE_SECURE,
    "csrf_secure": settings.CSRF_COOKIE_SECURE,
    "hsts": settings.SECURE_HSTS_SECONDS,
    "conn_max_age": settings.DATABASES["default"]["CONN_MAX_AGE"],
    "sslmode": settings.DATABASES["default"]["OPTIONS"].get("sslmode"),
    "renderers": settings.REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"],
    "num_proxies": settings.REST_FRAMEWORK["NUM_PROXIES"],
    "throttle_rates": settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
    "auth_classes": settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"],
}))
"""


def _load(extra_env=None):
    env = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "DEBUG")}
    env.update(
        DJANGO_SETTINGS_MODULE="config.settings.production",
        SECRET_KEY="x" * 60,
        ALLOWED_HOSTS="api.example.com",
        DATABASE_URL="postgres://u:p@db.example.com:5432/postgres",
    )
    env.update(extra_env or {})
    out = subprocess.run(
        [sys.executable, "-c", f"import django; django.setup(); {PROBE}"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def prod():
    return _load()


def test_debug_is_off_even_if_env_says_otherwise():
    assert _load({"DEBUG": "True"})["debug"] is False


def test_tls_hardening(prod):
    assert prod["proxy_header"] == ["HTTP_X_FORWARDED_PROTO", "https"]
    assert prod["session_secure"] is True
    assert prod["csrf_secure"] is True
    assert prod["hsts"] > 0


def test_database_requires_tls_and_reuses_connections(prod):
    assert prod["sslmode"] == "require"
    assert prod["conn_max_age"] > 0


def test_database_url_can_override_sslmode():
    loaded = _load(
        {
            "DATABASE_URL": "postgres://u:p@db.example.com:5432/postgres?sslmode=verify-full"
        }
    )
    assert loaded["sslmode"] == "verify-full"


def test_api_is_json_only_and_trusts_exactly_one_proxy(prod):
    assert prod["renderers"] == ["rest_framework.renderers.JSONRenderer"]
    assert prod["num_proxies"] == 1


def test_base_drf_settings_are_preserved(prod):
    assert prod["throttle_rates"]["auth"] == "5/min"
    assert prod["auth_classes"] == [
        "rest_framework_simplejwt.authentication.JWTAuthentication"
    ]
