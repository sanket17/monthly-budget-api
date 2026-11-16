from rest_framework.routers import SimpleRouter

from .views import CreditCardEntryViewSet, CreditCardViewSet

router = SimpleRouter()
router.register("credit-cards", CreditCardViewSet, basename="credit-card")
router.register("credit-card-entries", CreditCardEntryViewSet, basename="credit-card-entry")

credit_card_patterns = router.urls
