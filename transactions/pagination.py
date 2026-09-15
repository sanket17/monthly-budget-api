from rest_framework.pagination import PageNumberPagination


class TransactionPagination(PageNumberPagination):
    """
    TXNS-07: transaction lists are paginated. Scoped to this ViewSet only
    (set via TransactionViewSet.pagination_class) — do NOT make this the
    global DEFAULT_PAGINATION_CLASS, it would wrap CategoryViewSet and
    PlannedAmountViewSet responses in a paginated envelope and break their
    existing tests, which assert response.data is a plain list/dict.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
