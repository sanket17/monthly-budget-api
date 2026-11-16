import pytest


@pytest.mark.django_db
def test_healthz_is_public_and_cheap(api_client, django_assert_num_queries):
    with django_assert_num_queries(0):
        response = api_client.get("/healthz/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_swagger_ui_page_renders(api_client):
    """/api/schema/swagger-ui/ renders an HTML template, so the project needs
    a configured Django template engine even though it is API-only."""
    response = api_client.get("/api/schema/swagger-ui/")

    assert response.status_code == 200
    assert b"swagger-ui" in response.content.lower()
