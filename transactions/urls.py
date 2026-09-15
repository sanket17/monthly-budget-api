from rest_framework.routers import DefaultRouter

from .views import InitialBalanceViewSet, TransactionViewSet

router = DefaultRouter()
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("initial-balances", InitialBalanceViewSet, basename="initial-balance")

transaction_patterns = router.urls
