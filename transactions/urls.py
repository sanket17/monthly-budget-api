from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import BalanceSummaryView, InitialBalanceViewSet, TransactionViewSet

router = SimpleRouter()
router.register("transactions", TransactionViewSet, basename="transaction")
router.register("initial-balances", InitialBalanceViewSet, basename="initial-balance")

transaction_patterns = router.urls + [
    path("balance/", BalanceSummaryView.as_view(), name="balance-summary"),
]
