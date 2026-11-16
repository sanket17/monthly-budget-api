import pytest


@pytest.mark.django_db
def test_healthz_is_public_and_cheap(api_client, django_assert_num_queries):
    with django_assert_num_queries(0):
        response = api_client.get("/healthz/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
