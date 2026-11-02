import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
PASSWORD = "CorrectHorse2026!"
LOGIN_URL = "/api/v1/auth/login/"
REGISTER_URL = "/api/v1/auth/register/"
RESET_REQUEST_URL = "/api/v1/auth/password-reset/"


def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    assert client.get("/api/v1/auth/csrf/").status_code == 200
    return client


def post(client, url, payload, **extra):
    return client.post(
        url,
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        **extra,
    )


@pytest.mark.django_db
def test_login_is_throttled_per_target_email_across_ips():
    User.objects.create_user("victim@example.test", PASSWORD)
    client = csrf_client()

    for i in range(10):
        resp = post(
            client,
            LOGIN_URL,
            {"email": "victim@example.test", "password": f"wrong-{i}"},
            REMOTE_ADDR=f"10.1.0.{i + 1}",
        )
        assert resp.status_code == 401

    blocked = post(
        client,
        LOGIN_URL,
        {"email": " VICTIM@example.test ", "password": PASSWORD},
        REMOTE_ADDR="10.1.0.99",
    )
    assert blocked.status_code == 429
    assert blocked.data["error"]["code"] == "rate_limit_exceeded"


@pytest.mark.django_db
def test_login_is_throttled_per_ip_across_emails():
    client = csrf_client()

    for i in range(30):
        resp = post(
            client,
            LOGIN_URL,
            {"email": f"user{i}@example.test", "password": "wrong-password"},
            REMOTE_ADDR="10.2.0.1",
        )
        assert resp.status_code == 401

    blocked = post(
        client,
        LOGIN_URL,
        {"email": "user30@example.test", "password": "wrong-password"},
        REMOTE_ADDR="10.2.0.1",
    )
    assert blocked.status_code == 429


@pytest.mark.django_db
def test_registration_is_throttled_per_ip():
    client = csrf_client()

    for i in range(20):
        resp = post(
            client,
            REGISTER_URL,
            {"email": f"new{i}@example.test", "password": PASSWORD},
            REMOTE_ADDR="10.3.0.1",
        )
        assert resp.status_code == 201

    blocked = post(
        client,
        REGISTER_URL,
        {"email": "new20@example.test", "password": PASSWORD},
        REMOTE_ADDR="10.3.0.1",
    )
    assert blocked.status_code == 429
    assert not User.objects.filter(email="new20@example.test").exists()


@pytest.mark.django_db
def test_spoofed_x_forwarded_for_does_not_reset_ip_limit():
    client = csrf_client()

    for i in range(10):
        resp = post(
            client,
            RESET_REQUEST_URL,
            {"email": f"spoof{i}@example.test"},
            REMOTE_ADDR="10.4.0.1",
            HTTP_X_FORWARDED_FOR=f"203.0.113.{i + 1}",
        )
        assert resp.status_code == 200

    blocked = post(
        client,
        RESET_REQUEST_URL,
        {"email": "spoof10@example.test"},
        REMOTE_ADDR="10.4.0.1",
        HTTP_X_FORWARDED_FOR="198.51.100.77",
    )
    assert blocked.status_code == 429
