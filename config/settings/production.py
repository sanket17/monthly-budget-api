from .base import *  # noqa: F401,F403
from .base import DATABASES, REST_FRAMEWORK, env

DEBUG = False

# --- Behind a TLS-terminating reverse proxy (Caddy, see deploy/) -----------
# Caddy redirects http -> https itself, so SECURE_SSL_REDIRECT stays off:
# turning it on would also redirect plain-HTTP requests from inside the
# docker network. The proxy sets X-Forwarded-Proto; trust exactly that.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Start low so a mistake is recoverable; raise (e.g. 31536000) once HTTPS is
# confirmed working on the final domain.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
SECURE_CONTENT_TYPE_NOSNIFF = True

# --- Database ---------------------------------------------------------------
# Supabase requires TLS. Reuse connections for a minute (cheaper than a TLS
# handshake per request) but verify they are still alive before use.
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DATABASES["default"].setdefault("OPTIONS", {}).setdefault("sslmode", "require")

# --- DRF ---------------------------------------------------------------------
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    # JSON only: the browsable API needs static files this deployment does
    # not serve.
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # Exactly one trusted proxy (Caddy). Without this DRF believes the
    # client-supplied X-Forwarded-For, so anyone could dodge the per-IP
    # login/anon throttles by sending a fresh fake address on every request.
    "NUM_PROXIES": 1,
}
