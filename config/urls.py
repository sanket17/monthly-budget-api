from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from users.urls import auth_patterns, user_patterns

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # Auth endpoints: /api/auth/register/, /api/auth/login/, /api/auth/token/refresh/, /api/auth/logout/
    path("api/auth/", include(auth_patterns)),
    # User endpoints: /api/users/me/
    path("api/users/", include(user_patterns)),
]
