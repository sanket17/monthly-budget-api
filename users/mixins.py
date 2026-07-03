class UserScopedMixin:
    """
    Mixin for ViewSets that scope all data to the authenticated user.

    REQUIRED on every ModelViewSet that stores user-owned data.
    This mixin is the primary defense against OWASP API Top 10 #1
    (Broken Object Level Authorization / BOLA).

    Usage:
        class CategoryViewSet(UserScopedMixin, ModelViewSet):
            queryset = Category.objects.all()
            serializer_class = CategorySerializer
            permission_classes = [IsAuthenticated]
            # get_queryset() and perform_create() provided by UserScopedMixin

    Security guarantee:
        - get_queryset() always filters to request.user — no user can access another user's objects
        - perform_create() always sets user=request.user on save — no user can create objects for another user
    """

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
