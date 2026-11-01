import pytest
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

User = get_user_model()
PASSWORD = "CorrectHorse2026!"


def csrf_client():
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    assert response.data["csrf_token"]
    return client


def csrf_header(client):
    return {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}


@pytest.mark.django_db
def test_user_manager_identity_password_and_superuser():
    user = User.objects.create_user("  PERSON@Example.TEST  ", PASSWORD)
    assert user.email == "person@example.test"
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)
    assert authenticate(email="PERSON@example.test", password=PASSWORD) == user
    assert user.is_active and not user.is_staff and not user.is_superuser
    superuser = User.objects.create_superuser("root@example.test", PASSWORD)
    assert superuser.is_staff and superuser.is_superuser
    with pytest.raises(ValueError):
        User.objects.create_user("", PASSWORD)
    with pytest.raises(ValueError):
        User.objects.create_user("missing@example.test", "")
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            "broken@example.test", PASSWORD, is_superuser=False
        )


@pytest.mark.django_db
def test_database_enforces_case_insensitive_identity_and_alias():
    User.objects.create_user("first@example.test", PASSWORD)
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user("FIRST@example.test", PASSWORD)
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            "alias@example.test", PASSWORD, leaderboard_opt_in=True, public_alias="  "
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            "null-alias@example.test", PASSWORD, leaderboard_opt_in=True
        )


@pytest.mark.django_db
def test_registration_csrf_success_and_no_automatic_login():
    client = csrf_client()
    assert client.cookies["csrftoken"]["httponly"] == ""
    response = client.post(
        "/api/v1/auth/register/",
        {"email": "PERSON@Example.TEST", "password": PASSWORD},
        format="json",
        **csrf_header(client),
    )
    assert response.status_code == 201
    assert response.data == {
        "id": response.data["id"],
        "email": "person@example.test",
        "public_alias": None,
        "leaderboard_opt_in": False,
    }
    assert User.objects.get(pk=response.data["id"]).check_password(PASSWORD)
    assert "sessionid" not in client.cookies
    assert client.get("/api/v1/me/").status_code == 401


@pytest.mark.django_db
def test_registration_rejects_missing_csrf_and_invalid_data():
    client = APIClient(enforce_csrf_checks=True)
    no_csrf = client.post(
        "/api/v1/auth/register/",
        {"email": "valid@example.test", "password": PASSWORD},
        format="json",
    )
    assert no_csrf.status_code == 403
    assert no_csrf.json()["error"]["code"] == "csrf_failed"
    client = csrf_client()
    for payload in (
        {"email": "bad", "password": PASSWORD},
        {"email": "valid@example.test", "password": "short"},
        {"email": "valid@example.test"},
    ):
        response = client.post(
            "/api/v1/auth/register/", payload, format="json", **csrf_header(client)
        )
        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
    assert User.objects.count() == 0


@pytest.mark.django_db
def test_duplicate_email_and_privileged_fields_are_rejected():
    User.objects.create_user("taken@example.test", PASSWORD)
    client = csrf_client()
    duplicate = client.post(
        "/api/v1/auth/register/",
        {"email": "TAKEN@example.test", "password": PASSWORD},
        format="json",
        **csrf_header(client),
    )
    assert duplicate.status_code == 409
    assert duplicate.data["error"]["code"] == "email_taken"
    for field, value in (
        ("is_staff", True),
        ("is_superuser", True),
        ("is_active", True),
    ):
        response = client.post(
            "/api/v1/auth/register/",
            {"email": "new@example.test", "password": PASSWORD, field: value},
            format="json",
            **csrf_header(client),
        )
        assert response.status_code == 400
        assert response.data["error"]["code"] == "unknown_field"
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_login_session_rotation_refresh_logout_and_repeated_logout():
    user = User.objects.create_user("member@example.test", PASSWORD)
    client = csrf_client()
    old_csrf = client.cookies["csrftoken"].value
    assert (
        client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": PASSWORD},
            format="json",
        ).status_code
        == 403
    )
    response = client.post(
        "/api/v1/auth/login/",
        {"email": "MEMBER@example.test", "password": PASSWORD},
        format="json",
        **csrf_header(client),
    )
    assert response.status_code == 200
    assert response.data["id"] == user.pk
    assert "sessionid" in client.cookies
    assert client.cookies["sessionid"]["httponly"] is True
    assert client.cookies["csrftoken"].value != old_csrf
    assert client.get("/api/v1/me/").data["email"] == user.email
    assert client.post("/api/v1/auth/logout/").status_code == 403
    assert (
        client.post(
            "/api/v1/auth/logout/", {}, format="json", **csrf_header(client)
        ).status_code
        == 204
    )
    assert client.get("/api/v1/me/").status_code == 401
    repeated = client.post(
        "/api/v1/auth/logout/", {}, format="json", **csrf_header(client)
    )
    assert repeated.status_code == 401
    assert repeated["WWW-Authenticate"] == 'Session realm="api"'


@pytest.mark.django_db
def test_invalid_credentials_and_inactive_account_do_not_disclose_state():
    user = User.objects.create_user("member@example.test", PASSWORD)
    client = csrf_client()
    for email, password in (
        (user.email, "WrongPassword2026!"),
        ("unknown@example.test", PASSWORD),
    ):
        response = client.post(
            "/api/v1/auth/login/",
            {"email": email, "password": password},
            format="json",
            **csrf_header(client),
        )
        assert response.status_code == 401
        assert response.data["error"]["code"] == "invalid_credentials"
        assert response["WWW-Authenticate"] == 'Session realm="api"'
    user.is_active = False
    user.save(update_fields=["is_active"])
    response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
        **csrf_header(client),
    )
    assert response.status_code == 401
    assert response.data["error"]["code"] == "invalid_credentials"


@pytest.mark.django_db
def test_untrusted_origin_cannot_login_with_a_valid_csrf_cookie():
    User.objects.create_user("member@example.test", PASSWORD)
    client = csrf_client()
    response = client.post(
        "/api/v1/auth/login/",
        {"email": "member@example.test", "password": PASSWORD},
        format="json",
        HTTP_ORIGIN="https://untrusted.example",
        **csrf_header(client),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"
    assert "sessionid" not in client.cookies


@pytest.mark.django_db
def test_malformed_json_uses_the_documented_error_code():
    client = csrf_client()
    response = client.post(
        "/api/v1/auth/login/",
        data="{invalid",
        content_type="application/json",
        **csrf_header(client),
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "invalid_json"


@pytest.mark.django_db
def test_me_only_returns_the_authenticated_account():
    first = User.objects.create_user("first@example.test", PASSWORD)
    User.objects.create_user("second@example.test", PASSWORD)
    client = csrf_client()
    client.post(
        "/api/v1/auth/login/",
        {"email": first.email, "password": PASSWORD},
        format="json",
        **csrf_header(client),
    )
    response = client.get("/api/v1/me/")
    assert response.status_code == 200
    assert response.data["id"] == first.pk
    assert response.data["email"] == first.email
    assert set(response.data) == {"id", "email", "public_alias", "leaderboard_opt_in"}


@pytest.mark.django_db
def test_deactivation_revokes_existing_session():
    user = User.objects.create_user("member@example.test", PASSWORD)
    client = csrf_client()
    client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
        **csrf_header(client),
    )
    user.is_active = False
    user.save(update_fields=["is_active"])
    assert client.get("/api/v1/me/").status_code == 401


@pytest.mark.django_db
def test_me_patch_requires_session_csrf_and_valid_opt_in_alias():
    user = User.objects.create_user("member@example.test", PASSWORD)
    client = csrf_client()
    anonymous = client.patch("/api/v1/me/", {"leaderboard_opt_in": True}, format="json")
    assert anonymous.status_code == 401
    client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
        **csrf_header(client),
    )
    assert (
        client.patch("/api/v1/me/", {"public_alias": "Fit"}, format="json").status_code
        == 403
    )
    no_alias = client.patch(
        "/api/v1/me/",
        {"leaderboard_opt_in": True},
        format="json",
        **csrf_header(client),
    )
    assert no_alias.status_code == 400
    assert "public_alias" in no_alias.data["error"]["fields"]
    response = client.patch(
        "/api/v1/me/",
        {"public_alias": "Fit", "leaderboard_opt_in": True},
        format="json",
        **csrf_header(client),
    )
    assert response.status_code == 200
    assert response.data["public_alias"] == "Fit"
    assert response.data["leaderboard_opt_in"] is True
    user.refresh_from_db()
    assert user.public_alias == "Fit" and user.leaderboard_opt_in
    assert (
        client.patch(
            "/api/v1/me/", {"is_staff": True}, format="json", **csrf_header(client)
        ).data["error"]["code"]
        == "unknown_field"
    )


@pytest.mark.django_db
def test_admin_deactivation_requires_explicit_permission():
    staff = User.objects.create_user("staff@example.test", PASSWORD, is_staff=True)
    target = User.objects.create_user("target@example.test", PASSWORD)
    client = APIClient()
    client.force_login(staff)
    assert client.get("/admin/accounts/user/").status_code == 403
    group = Group.objects.create(name="Administrator")
    group.permissions.add(Permission.objects.get(codename="deactivate_user"))
    staff.groups.add(group)
    staff = User.objects.get(pk=staff.pk)
    client.force_login(staff)
    assert client.get("/admin/accounts/user/").status_code == 200
    assert client.get(f"/admin/accounts/user/{target.pk}/change/").status_code == 403
    response = client.post(
        "/admin/accounts/user/",
        {"action": "deactivate_accounts", "_selected_action": [target.pk, staff.pk]},
    )
    assert response.status_code == 302
    target.refresh_from_db()
    staff.refresh_from_db()
    assert not target.is_active and staff.is_active


@pytest.mark.django_db
def test_technical_superuser_can_assign_staff_group_without_password_exposure():
    root = User.objects.create_superuser("root@example.test", PASSWORD)
    member = User.objects.create_user("member@example.test", PASSWORD)
    group = Group.objects.create(name="Administrator")
    group.permissions.add(Permission.objects.get(codename="deactivate_user"))
    client = APIClient()
    client.force_login(root)
    page = client.get(f"/admin/accounts/user/{member.pk}/change/")
    assert page.status_code == 200
    assert "password" not in page.context["adminform"].form.fields
    response = client.post(
        f"/admin/accounts/user/{member.pk}/change/",
        {"is_active": "on", "is_staff": "on", "groups": [group.pk], "_save": "Save"},
    )
    assert response.status_code == 302
    member.refresh_from_db()
    assert member.is_staff and member.groups.filter(pk=group.pk).exists()
