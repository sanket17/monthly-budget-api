from rest_framework.routers import DefaultRouter

from .views import RecurringEntryViewSet

router = DefaultRouter()
router.register("recurring-entries", RecurringEntryViewSet, basename="recurring-entry")

recurring_patterns = router.urls
