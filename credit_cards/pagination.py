from rest_framework.pagination import PageNumberPagination


class CreditCardEntryPagination(PageNumberPagination):
    """
    G6: credit-card-entry lists are paginated, same shape and limits as
    transactions/pagination.py::TransactionPagination (kept as its own
    class so the two endpoints can diverge). Scoped to
    CreditCardEntryViewSet only — never the global default, which would
    wrap the other list endpoints in a paginated envelope.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
