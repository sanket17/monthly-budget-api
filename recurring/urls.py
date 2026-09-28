from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import GenerateRecurringEntriesView, RecurringEntryViewSet

router = DefaultRouter()
router.register("recurring-entries", RecurringEntryViewSet, basename="recurring-entry")

# NOTE: the explicit generate/ path MUST precede router.urls. DRF's default
# detail route (`recurring-entries/(?P<pk>[^/.]+)/$`) uses a lookup regex
# that matches ANY non-slash/non-dot string — including the literal
# "generate". Django's resolver tries urlpatterns in list order and stops
# at the first regex match, before HTTP method dispatch is considered, so
# if router.urls came first, a POST to recurring-entries/generate/ would
# match the detail route (pk="generate") and 405 instead of ever reaching
# this view.
recurring_patterns = [
    path(
        "recurring-entries/generate/",
        GenerateRecurringEntriesView.as_view(),
        name="recurring-generate",
    ),
] + router.urls
