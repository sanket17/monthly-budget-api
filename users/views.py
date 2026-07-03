from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import RegistrationSerializer, UserProfileSerializer


class RegisterView(APIView):
    """
    POST /api/auth/register/

    Register a new user. Returns 201 with user data on success.
    Rate-limited to 5/min (auth scope) to deter credential stuffing.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        request=RegistrationSerializer,
        responses={201: RegistrationSerializer},
        description="Register a new user with email and password.",
    )
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProfileView(RetrieveUpdateAPIView):
    """
    GET/PATCH /api/users/me/

    Returns or updates the authenticated user's own profile.
    Scoped strictly to request.user — no user ID in the URL
    (prevents BOLA: attacker cannot substitute another user's ID).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    http_method_names = ["get", "patch", "head", "options"]  # No PUT

    @extend_schema(
        responses={200: UserProfileSerializer},
        description="Retrieve the authenticated user's profile.",
    )
    def get_object(self):
        return self.request.user
