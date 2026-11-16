from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, PlannedAmountViewSet

router = SimpleRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("planned-amounts", PlannedAmountViewSet, basename="planned-amount")

budget_patterns = router.urls
urlpatterns = budget_patterns
