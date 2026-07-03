from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")

# Combined so config/urls.py can include() this — extended in Plan 02-04
# when PlannedAmountViewSet is registered on the same router.
budget_patterns = router.urls
urlpatterns = budget_patterns
