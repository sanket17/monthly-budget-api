from datetime import date

from rest_framework.exceptions import ValidationError


def parse_month_param(request) -> date:
    """
    Parses ?month=YYYY-MM or ?month=YYYY-MM-DD from the request query
    params into a normalized first-of-month date. Defaults to the first
    day of the current calendar month if no ?month= param is given
    (calendar month is the budget period — CLAUDE.md data model constraint).
    """
    raw = request.query_params.get("month")
    if not raw:
        return date.today().replace(day=1)
    parts = raw.split("-")
    try:
        if len(parts) not in (2, 3):
            raise ValueError("Unexpected number of date parts")
        year, month = int(parts[0]), int(parts[1])
        return date(year, month, 1)
    except (ValueError, TypeError):
        raise ValidationError({"month": "Must be in YYYY-MM or YYYY-MM-DD format."})
