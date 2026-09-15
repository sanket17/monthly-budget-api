from rest_framework.routers import DefaultRouter

from .views import CreditCardViewSet

router = DefaultRouter()
router.register("credit-cards", CreditCardViewSet, basename="credit-card")

credit_card_patterns = router.urls
