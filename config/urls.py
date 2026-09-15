from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from budget.urls import budget_patterns
from credit_cards.urls import credit_card_patterns
from transactions.urls import transaction_patterns
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
    # Budget endpoints: /api/categories/, /api/planned-amounts/
    path("api/", include(budget_patterns)),
    # Transaction endpoints: /api/transactions/, /api/initial-balances/, /api/balance/
    path("api/", include(transaction_patterns)),
    # Credit card endpoints: /api/credit-cards/ (router already prefixes credit-cards/)
    path("api/", include(credit_card_patterns)),
]
