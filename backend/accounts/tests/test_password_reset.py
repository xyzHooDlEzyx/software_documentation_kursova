import re
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.db import connections
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from accounts.errors import ResetTokenInvalidOrExpired
from accounts.services import PasswordResetService

User = get_user_model()
PASSWORD = "CorrectHorse2026!"
NEW_PASSWORD = "UpdatedHorse2026!"
ALT_PASSWORD = "AlternateHorse2026!"

RESET_REQUEST_URL = "/api/v1/auth/password-reset/"
RESET_CONFIRM_URL = "/api/v1/auth/password-reset/confirm/"
RESET_REQUEST_MESSAGE = (
    "Якщо акаунт із такою адресою існує, "
    "ми надішлемо інструкції для відновлення пароля."
)
RESET_CONFIRM_MESSAGE = "Пароль оновлено. Увійдіть із новим паролем."
RESET_LINK_RE = re.compile(
    r"http://localhost:5173/reset-password/(?P<uid>[^/\s]+)/(?P<token>[^\s]+)"
)


def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    assert response.data["csrf_token"]
    return client


def csrf_header(client):
    return {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}


def extract_uid_and_token(body: str) -> tuple[str, str]:
    match = RESET_LINK_RE.search(body)
    assert match is not None
    return match.group("uid"), match.group("token")


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_password_reset_request_active_user_sends_email_without_session_or_leakage(
    caplog,
):
    user = User.objects.create_user("Member@Example.TEST", PASSWORD)
    client = csrf_client()
    with caplog.at_level("DEBUG"):
        response = client.post(
            RESET_REQUEST_URL,
            {"email": "  MEMBER@example.test  "},
            format="json",
            **csrf_header(client),
        )
    assert response.status_code == 200
    assert response.json() == {"message": RESET_REQUEST_MESSAGE}
    assert "sessionid" not in client.cookies
    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.to == [user.email]
    assert sent.subject == "Відновлення пароля у Фітнес-трекері"
    assert "60 хвилин" in sent.body
    uid, token = extract_uid_and_token(sent.body)
    assert f"http://localhost:5173/reset-password/{uid}/{token}" in sent.body
    raw_response = response.content.decode("utf-8")
    assert token not in raw_response
    assert uid not in raw_response
    assert token not in caplog.text
    assert f"/reset-password/{uid}/" not in caplog.text


@pytest.mark.django_db
def test_password_reset_request_anti_enumeration_for_unknown_inactive_and_unusable():
    inactive = User.objects.create_user(
        "inactive@example.test", PASSWORD, is_active=False
    )
    unusable = User.objects.create_user("unusable@example.test", PASSWORD)
    unusable.set_unusable_password()
    unusable.save(update_fields=["password"])

    client = csrf_client()
    for target_email in (
        "unknown@example.test",
        inactive.email,
        unusable.email,
    ):
        response = client.post(
            RESET_REQUEST_URL,
            {"email": target_email},
            format="json",
            **csrf_header(client),
        )
        assert response.status_code == 200
        assert response.json() == {"message": RESET_REQUEST_MESSAGE}
        assert "sessionid" not in client.cookies

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_endpoints_reject_invalid_payloads_and_unknown_fields():
    client = csrf_client()
    for invalid_payload in (
        {"email": "not-an-email"},
        {"email": ""},
        {},
    ):
        response = client.post(
            RESET_REQUEST_URL,
            invalid_payload,
            format="json",
            **csrf_header(client),
        )
        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert "email" in response.data["error"]["fields"]

    unknown_a07 = client.post(
        RESET_REQUEST_URL,
        {"email": "person@example.test", "extra": "value"},
        format="json",
        **csrf_header(client),
    )
    assert unknown_a07.status_code == 400
    assert unknown_a07.data["error"]["code"] == "unknown_field"
    assert "extra" in unknown_a07.data["error"]["fields"]

    unknown_a08 = client.post(
        RESET_CONFIRM_URL,
        {
            "uid": "MQ",
            "token": "some-token",
            "new_password": NEW_PASSWORD,
            "unexpected": True,
        },
        format="json",
        **csrf_header(client),
    )
    assert unknown_a08.status_code == 400
    assert unknown_a08.data["error"]["code"] == "unknown_field"
    assert "unexpected" in unknown_a08.data["error"]["fields"]

    missing_a08 = client.post(
        RESET_CONFIRM_URL,
        {"uid": "MQ"},
        format="json",
        **csrf_header(client),
    )
    assert missing_a08.status_code == 400
    assert missing_a08.data["error"]["code"] == "validation_error"
    assert "token" in missing_a08.data["error"]["fields"]
    assert "new_password" in missing_a08.data["error"]["fields"]


@pytest.mark.django_db
def test_password_reset_endpoints_enforce_csrf_and_trusted_origin():
    raw_client = APIClient(enforce_csrf_checks=True)
    missing_csrf_a07 = raw_client.post(
        RESET_REQUEST_URL,
        {"email": "member@example.test"},
        format="json",
    )
    assert missing_csrf_a07.status_code == 403
    assert missing_csrf_a07.json()["error"]["code"] == "csrf_failed"

    missing_csrf_a08 = raw_client.post(
        RESET_CONFIRM_URL,
        {"uid": "MQ", "token": "tok", "new_password": NEW_PASSWORD},
        format="json",
    )
    assert missing_csrf_a08.status_code == 403
    assert missing_csrf_a08.json()["error"]["code"] == "csrf_failed"

    client = csrf_client()
    evil_a07 = client.post(
        RESET_REQUEST_URL,
        {"email": "member@example.test"},
        format="json",
        HTTP_ORIGIN="https://evil.example",
        **csrf_header(client),
    )
    assert evil_a07.status_code == 403
    assert evil_a07.json()["error"]["code"] == "csrf_failed"

    evil_a08 = client.post(
        RESET_CONFIRM_URL,
        {"uid": "MQ", "token": "tok", "new_password": NEW_PASSWORD},
        format="json",
        HTTP_ORIGIN="https://evil.example",
        **csrf_header(client),
    )
    assert evil_a08.status_code == 403
    assert evil_a08.json()["error"]["code"] == "csrf_failed"


@pytest.mark.django_db
def test_password_reset_confirm_updates_hash_and_revokes_session():
    user = User.objects.create_user("member@example.test", PASSWORD)

    session_client = csrf_client()
    login_resp = session_client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
        **csrf_header(session_client),
    )
    assert login_resp.status_code == 200
    assert session_client.get("/api/v1/me/").status_code == 200

    reset_client = csrf_client()
    req_resp = reset_client.post(
        RESET_REQUEST_URL,
        {"email": user.email},
        format="json",
        **csrf_header(reset_client),
    )
    assert req_resp.status_code == 200
    assert len(mail.outbox) == 1
    uid, token = extract_uid_and_token(mail.outbox[0].body)

    confirm_resp = reset_client.post(
        RESET_CONFIRM_URL,
        {"uid": uid, "token": token, "new_password": NEW_PASSWORD},
        format="json",
        **csrf_header(reset_client),
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json() == {"message": RESET_CONFIRM_MESSAGE}
    assert "sessionid" not in reset_client.cookies

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD) is True
    assert user.check_password(PASSWORD) is False

    old_session_me = session_client.get("/api/v1/me/")
    assert old_session_me.status_code == 401
    assert old_session_me.data["error"]["code"] == "authentication_required"

    old_login = reset_client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
        **csrf_header(reset_client),
    )
    assert old_login.status_code == 401
    assert old_login.data["error"]["code"] == "invalid_credentials"

    new_login = reset_client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": NEW_PASSWORD},
        format="json",
        **csrf_header(reset_client),
    )
    assert new_login.status_code == 200
    assert new_login.data["id"] == user.pk


@pytest.mark.django_db
def test_password_reset_token_cannot_be_reused():
    user = User.objects.create_user("member@example.test", PASSWORD)
    client = csrf_client()
    client.post(
        RESET_REQUEST_URL,
        {"email": user.email},
        format="json",
        **csrf_header(client),
    )
    uid, token = extract_uid_and_token(mail.outbox[0].body)

    first = client.post(
        RESET_CONFIRM_URL,
        {"uid": uid, "token": token, "new_password": NEW_PASSWORD},
        format="json",
        **csrf_header(client),
    )
    assert first.status_code == 200

    second = client.post(
        RESET_CONFIRM_URL,
        {"uid": uid, "token": token, "new_password": ALT_PASSWORD},
        format="json",
        **csrf_header(client),
    )
    assert second.status_code == 400
    assert second.data["error"]["code"] == "reset_token_invalid_or_expired"
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD) is True
    assert user.check_password(ALT_PASSWORD) is False


@pytest.mark.django_db
def test_password_reset_confirm_rejects_invalid_malformed_and_expired_tokens():
    user = User.objects.create_user("member@example.test", PASSWORD)
    other = User.objects.create_user("other@example.test", PASSWORD)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    valid_token = default_token_generator.make_token(user)
    other_token = default_token_generator.make_token(other)

    client = csrf_client()
    invalid_cases = [
        (uid, valid_token[:-1] + ("0" if valid_token[-1] != "0" else "1")),
        ("!!!not-valid-int!!!", valid_token),
        (urlsafe_base64_encode(force_bytes(0)), valid_token),
        (urlsafe_base64_encode(force_bytes(-5)), valid_token),
        (urlsafe_base64_encode(force_bytes(99999999)), valid_token),
        (uid, other_token),
    ]
    for case_uid, case_token in invalid_cases:
        response = client.post(
            RESET_CONFIRM_URL,
            {"uid": case_uid, "token": case_token, "new_password": NEW_PASSWORD},
            format="json",
            **csrf_header(client),
        )
        assert response.status_code == 400
        assert response.data["error"]["code"] == "reset_token_invalid_or_expired"

    with override_settings(PASSWORD_RESET_TIMEOUT=-1):
        expired = client.post(
            RESET_CONFIRM_URL,
            {"uid": uid, "token": valid_token, "new_password": NEW_PASSWORD},
            format="json",
            **csrf_header(client),
        )
    assert expired.status_code == 400
    assert expired.data["error"]["code"] == "reset_token_invalid_or_expired"

    user.is_active = False
    user.save(update_fields=["is_active"])
    deactivated = client.post(
        RESET_CONFIRM_URL,
        {"uid": uid, "token": valid_token, "new_password": NEW_PASSWORD},
        format="json",
        **csrf_header(client),
    )
    assert deactivated.status_code == 400
    assert deactivated.data["error"]["code"] == "reset_token_invalid_or_expired"


@pytest.mark.django_db
def test_password_reset_confirm_validates_password_without_consuming_token():
    user = User.objects.create_user("member@example.test", PASSWORD)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    client = csrf_client()

    for weak_password in (
        "short123!",
        "1234567890123",
        "member@example.test",
    ):
        response = client.post(
            RESET_CONFIRM_URL,
            {"uid": uid, "token": token, "new_password": weak_password},
            format="json",
            **csrf_header(client),
        )
        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert "new_password" in response.data["error"]["fields"]

    user.refresh_from_db()
    assert user.check_password(PASSWORD) is True

    success = client.post(
        RESET_CONFIRM_URL,
        {"uid": uid, "token": token, "new_password": NEW_PASSWORD},
        format="json",
        **csrf_header(client),
    )
    assert success.status_code == 200
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD) is True


@pytest.mark.django_db
def test_password_reset_throttling_per_email_and_per_ip():
    user = User.objects.create_user("member@example.test", PASSWORD)
    client = csrf_client()

    for i in range(5):
        resp = client.post(
            RESET_REQUEST_URL,
            {"email": user.email},
            format="json",
            REMOTE_ADDR=f"10.0.1.{i + 1}",
            **csrf_header(client),
        )
        assert resp.status_code == 200
    sixth_existing = client.post(
        RESET_REQUEST_URL,
        {"email": "  MEMBER@Example.test "},
        format="json",
        REMOTE_ADDR="10.0.1.99",
        **csrf_header(client),
    )
    assert sixth_existing.status_code == 429
    assert sixth_existing.data["error"]["code"] == "rate_limit_exceeded"

    for i in range(5):
        resp = client.post(
            RESET_REQUEST_URL,
            {"email": "nonexistent@example.test"},
            format="json",
            REMOTE_ADDR=f"10.0.2.{i + 1}",
            **csrf_header(client),
        )
        assert resp.status_code == 200
    sixth_nonexistent = client.post(
        RESET_REQUEST_URL,
        {"email": "NONEXISTENT@example.test"},
        format="json",
        REMOTE_ADDR="10.0.2.99",
        **csrf_header(client),
    )
    assert sixth_nonexistent.status_code == 429
    assert sixth_nonexistent.data["error"]["code"] == "rate_limit_exceeded"

    cache.clear()
    for i in range(10):
        resp = client.post(
            RESET_REQUEST_URL,
            {"email": f"user{i}@example.test"},
            format="json",
            REMOTE_ADDR="10.0.3.1",
            **csrf_header(client),
        )
        assert resp.status_code == 200
    eleventh_ip = client.post(
        RESET_REQUEST_URL,
        {"email": "user10@example.test"},
        format="json",
        REMOTE_ADDR="10.0.3.1",
        **csrf_header(client),
    )
    assert eleventh_ip.status_code == 429
    assert eleventh_ip.data["error"]["code"] == "rate_limit_exceeded"

    cache.clear()
    for _ in range(10):
        resp = client.post(
            RESET_CONFIRM_URL,
            {"uid": "MQ", "token": "bad-token", "new_password": NEW_PASSWORD},
            format="json",
            REMOTE_ADDR="10.0.4.1",
            **csrf_header(client),
        )
        assert resp.status_code == 400
    eleventh_confirm_ip = client.post(
        RESET_CONFIRM_URL,
        {"uid": "MQ", "token": "bad-token", "new_password": NEW_PASSWORD},
        format="json",
        REMOTE_ADDR="10.0.4.1",
        **csrf_header(client),
    )
    assert eleventh_confirm_ip.status_code == 429
    assert eleventh_confirm_ip.data["error"]["code"] == "rate_limit_exceeded"


@pytest.mark.django_db(transaction=True)
def test_concurrent_password_reset_confirm_allows_only_one_winner():
    user = User.objects.create_user("concurrent@example.test", PASSWORD)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    def attempt_reset(candidate_password: str) -> str:
        try:
            PasswordResetService().confirm_reset(
                uid=uid, token=token, new_password=candidate_password
            )
            return candidate_password
        finally:
            connections.close_all()

    passwords = [NEW_PASSWORD, ALT_PASSWORD]
    successes = []
    failures = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(attempt_reset, pwd) for pwd in passwords]
        for future in futures:
            try:
                successes.append(future.result())
            except ResetTokenInvalidOrExpired as exc:
                failures.append(exc)

    assert len(successes) == 1
    assert len(failures) == 1
    user.refresh_from_db()
    assert user.check_password(successes[0]) is True
