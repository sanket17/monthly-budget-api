from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, PlannedAmountViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("planned-amounts", PlannedAmountViewSet, basename="planned-amount")

budget_patterns = router.urls
urlpatterns = budget_patterns
