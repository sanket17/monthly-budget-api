from django.urls import path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import ProfileView, RegisterView

# Auth endpoints — imported into config/urls.py under /api/auth/
auth_patterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", TokenBlacklistView.as_view(), name="token_blacklist"),
]

# User endpoints — imported into config/urls.py under /api/users/
user_patterns = [
    path("me/", ProfileView.as_view(), name="profile"),
]

# Combined so Django can locate the module (used by tests that import from users.urls)
urlpatterns = auth_patterns + user_patterns
