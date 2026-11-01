from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, connections, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.errors import ProfileExists
from accounts.models import (
    ExperienceLevel,
    FitnessGoal,
    Gender,
    Profile,
    WeightEntry,
)
from accounts.services import ProfileService

User = get_user_model()
PASSWORD = "CorrectHorse2026!"
KYIV_TZ = ZoneInfo("Europe/Kyiv")
PROFILE_URL = "/api/v1/profile/"
WEIGHT_ENTRIES_URL = "/api/v1/weight-entries/"


def csrf_client() -> APIClient:
    client = APIClient(enforce_csrf_checks=True)
    response = client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    assert response.data["csrf_token"]
    return client


def csrf_header(client: APIClient) -> dict[str, str]:
    return {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value}


def auth_csrf_client(user) -> APIClient:
    client = csrf_client()
    response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
        **csrf_header(client),
    )
    assert response.status_code == 200
    return client


def valid_profile_payload(**overrides) -> dict:
    payload = {
        "date_of_birth": "1998-05-14",
        "weight_kg": "68.4",
        "height_cm": "170.0",
        "gender": "female",
        "fitness_goal": "weight_loss",
        "experience_level": "intermediate",
        "workouts_per_week": 3,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_profile_create_valid_defaults_and_initial_weight_entry(monkeypatch):
    fixed_now = datetime(2026, 4, 15, 10, 30, 0, tzinfo=dt_timezone.utc)
    monkeypatch.setattr(timezone, "now", lambda: fixed_now)

    user = User.objects.create_user("user1@example.test", PASSWORD)
    client = auth_csrf_client(user)

    response = client.post(
        PROFILE_URL,
        valid_profile_payload(),
        format="json",
        **csrf_header(client),
    )
    assert response.status_code == 201
    assert response.json() == {
        "first_name": "",
        "last_name": "",
        "date_of_birth": "1998-05-14",
        "age": 27,
        "weight_kg": "68.4",
        "height_cm": "170.0",
        "gender": "female",
        "fitness_goal": "weight_loss",
        "experience_level": "intermediate",
        "workouts_per_week": 3,
    }

    profile = Profile.objects.get(user=user)
    assert profile.first_name == ""
    assert profile.last_name == ""
    assert profile.weight_kg == Decimal("68.4")
    assert profile.height_cm == Decimal("170.0")
    assert profile.created_at == fixed_now

    entries = list(WeightEntry.objects.filter(user=user))
    assert len(entries) == 1
    assert entries[0].weight_kg == Decimal("68.4")
    assert entries[0].measured_at == profile.created_at


@pytest.mark.django_db
def test_profile_create_with_explicit_first_and_last_name():
    user = User.objects.create_user("named@example.test", PASSWORD)
    client = auth_csrf_client(user)

    response = client.post(
        PROFILE_URL,
        valid_profile_payload(first_name="Олена", last_name="Коваленко"),
        format="json",
        **csrf_header(client),
    )
    assert response.status_code == 201
    assert response.data["first_name"] == "Олена"
    assert response.data["last_name"] == "Коваленко"

    profile = Profile.objects.get(user=user)
    assert profile.first_name == "Олена"
    assert profile.last_name == "Коваленко"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "missing_field",
    [
        "date_of_birth",
        "weight_kg",
        "height_cm",
        "gender",
        "fitness_goal",
        "experience_level",
        "workouts_per_week",
    ],
)
def test_profile_create_missing_required_fields_rejected(missing_field):
    user = User.objects.create_user("missing@example.test", PASSWORD)
    client = auth_csrf_client(user)

    payload = valid_profile_payload()
    payload.pop(missing_field)

    response = client.post(
        PROFILE_URL,
        payload,
        format="json",
        **csrf_header(client),
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
    assert missing_field in response.data["error"]["fields"]
    assert Profile.objects.filter(user=user).count() == 0
    assert WeightEntry.objects.filter(user=user).count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("bad_dob", ["not-a-date", "14-05-1998", "2000/01/01", ""])
def test_profile_create_invalid_date_of_birth_format(bad_dob):
    user = User.objects.create_user("baddob@example.test", PASSWORD)
    client = auth_csrf_client(user)

    response = client.post(
        PROFILE_URL,
        valid_profile_payload(date_of_birth=bad_dob),
        format="json",
        **csrf_header(client),
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
    assert "date_of_birth" in response.data["error"]["fields"]
    assert Profile.objects.count() == 0


@pytest.mark.django_db
def test_profile_create_age_boundaries_and_kyiv_timezone_edge_case(monkeypatch):
    # 2026-06-14T22:30:00Z is 2026-06-15T01:30:00+03:00 in Europe/Kyiv
    fixed_now = datetime(2026, 6, 14, 22, 30, 0, tzinfo=dt_timezone.utc)
    monkeypatch.setattr(timezone, "now", lambda: fixed_now)

    # 1. Age < 19 (1 day before 19th birthday in Europe/Kyiv: born 2007-06-16 -> age 18)
    user_18 = User.objects.create_user("age18@example.test", PASSWORD)
    client_18 = auth_csrf_client(user_18)
    resp_18 = client_18.post(
        PROFILE_URL,
        valid_profile_payload(date_of_birth="2007-06-16"),
        format="json",
        **csrf_header(client_18),
    )
    assert resp_18.status_code == 400
    assert resp_18.data["error"]["code"] == "validation_error"
    assert "date_of_birth" in resp_18.data["error"]["fields"]

    # 2. Exact 19th birthday on Europe/Kyiv local date (born 2007-06-15 -> age 19 in
    # Kyiv, even though UTC date is still 2026-06-14)
    user_19 = User.objects.create_user("age19@example.test", PASSWORD)
    client_19 = auth_csrf_client(user_19)
    resp_19 = client_19.post(
        PROFILE_URL,
        valid_profile_payload(date_of_birth="2007-06-15"),
        format="json",
        **csrf_header(client_19),
    )
    assert resp_19.status_code == 201
    assert resp_19.data["age"] == 19

    # 3. Day before 60th birthday on Europe/Kyiv local date (born 1966-06-16 -> age 59)
    user_59 = User.objects.create_user("age59@example.test", PASSWORD)
    client_59 = auth_csrf_client(user_59)
    resp_59 = client_59.post(
        PROFILE_URL,
        valid_profile_payload(date_of_birth="1966-06-16"),
        format="json",
        **csrf_header(client_59),
    )
    assert resp_59.status_code == 201
    assert resp_59.data["age"] == 59

    # 4. Exact 60th birthday on Europe/Kyiv local date (born 1966-06-15 -> age 60 > 59)
    user_60 = User.objects.create_user("age60@example.test", PASSWORD)
    client_60 = auth_csrf_client(user_60)
    resp_60 = client_60.post(
        PROFILE_URL,
        valid_profile_payload(date_of_birth="1966-06-15"),
        format="json",
        **csrf_header(client_60),
    )
    assert resp_60.status_code == 400
    assert resp_60.data["error"]["code"] == "validation_error"
    assert "date_of_birth" in resp_60.data["error"]["fields"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "field,invalid_values",
    [
        ("weight_kg", ["19.9", "500.1", "68.45", True, False, "abc", None]),
        ("height_cm", ["99.9", "250.1", "170.55", False, True, "xyz", None]),
        ("workouts_per_week", [0, 8, -1, 3.5, True, False, "many", None]),
        ("gender", ["unknown", "MALE", ""]),
        ("fitness_goal", ["bulking", "WEIGHT_LOSS", ""]),
        ("experience_level", ["pro", "BEGINNER", ""]),
        ("first_name", [None, "a" * 151]),
        ("last_name", [None, "b" * 151]),
    ],
)
def test_profile_create_field_validation_errors(field, invalid_values):
    user = User.objects.create_user(f"invalid_{field}@example.test", PASSWORD)
    client = auth_csrf_client(user)

    for bad_value in invalid_values:
        response = client.post(
            PROFILE_URL,
            valid_profile_payload(**{field: bad_value}),
            format="json",
            **csrf_header(client),
        )
        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert field in response.data["error"]["fields"]

    assert Profile.objects.filter(user=user).count() == 0
    assert WeightEntry.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_profile_create_duplicate_returns_409_profile_exists():
    user = User.objects.create_user("dup@example.test", PASSWORD)
    client = auth_csrf_client(user)

    first = client.post(
        PROFILE_URL,
        valid_profile_payload(),
        format="json",
        **csrf_header(client),
    )
    assert first.status_code == 201

    second = client.post(
        PROFILE_URL,
        valid_profile_payload(weight_kg="75.0"),
        format="json",
        **csrf_header(client),
    )
    assert second.status_code == 409
    assert second.data["error"]["code"] == "profile_exists"
    assert Profile.objects.filter(user=user).count() == 1
    assert WeightEntry.objects.filter(user=user).count() == 1
    assert Profile.objects.get(user=user).weight_kg == Decimal("68.4")


@pytest.mark.django_db(transaction=True)
def test_concurrent_profile_creation_allows_only_one_winner():
    user = User.objects.create_user("concurrent_create@example.test", PASSWORD)
    data = {
        "first_name": "Іван",
        "last_name": "Франко",
        "date_of_birth": date(1995, 8, 27),
        "weight_kg": Decimal("75.0"),
        "height_cm": Decimal("178.0"),
        "gender": Gender.MALE,
        "fitness_goal": FitnessGoal.MAINTENANCE,
        "experience_level": ExperienceLevel.INTERMEDIATE,
        "workouts_per_week": 4,
    }

    def worker():
        try:
            ProfileService.create_profile(user, data)
            return "created"
        except ProfileExists:
            return "profile_exists"
        finally:
            connection.close()
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(worker) for _ in range(2)]
        results = [f.result() for f in futures]

    assert sorted(results) == ["created", "profile_exists"]
    assert Profile.objects.filter(user=user).count() == 1
    assert WeightEntry.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_profile_create_atomic_rollback_when_weight_entry_fails(monkeypatch):
    user = User.objects.create_user("rollback_create@example.test", PASSWORD)
    client = auth_csrf_client(user)

    def boom(*args, **kwargs):
        raise IntegrityError("Simulated WeightEntry failure")

    monkeypatch.setattr(WeightEntry.objects, "create", boom)

    with pytest.raises(IntegrityError):
        client.post(
            PROFILE_URL,
            valid_profile_payload(),
            format="json",
            **csrf_header(client),
        )

    assert Profile.objects.filter(user=user).count() == 0
    assert WeightEntry.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_database_check_constraints_enforced_directly_on_models():
    user = User.objects.create_user("constraints@example.test", PASSWORD)
    base_kwargs = {
        "user": user,
        "first_name": "",
        "last_name": "",
        "date_of_birth": date(1995, 5, 5),
        "weight_kg": Decimal("70.0"),
        "height_cm": Decimal("175.0"),
        "gender": Gender.MALE,
        "fitness_goal": FitnessGoal.MAINTENANCE,
        "experience_level": ExperienceLevel.BEGINNER,
        "workouts_per_week": 3,
    }

    invalid_profile_overrides = [
        {"weight_kg": Decimal("19.9")},
        {"weight_kg": Decimal("500.1")},
        {"height_cm": Decimal("99.9")},
        {"height_cm": Decimal("250.1")},
        {"workouts_per_week": 0},
        {"workouts_per_week": 8},
        {"gender": "invalid_gender"},
        {"fitness_goal": "invalid_goal"},
        {"experience_level": "invalid_level"},
    ]

    for override in invalid_profile_overrides:
        kwargs = {**base_kwargs, **override}
        with pytest.raises(IntegrityError), transaction.atomic():
            Profile.objects.create(**kwargs)

    for bad_weight in (Decimal("19.9"), Decimal("500.1")):
        with pytest.raises(IntegrityError), transaction.atomic():
            WeightEntry.objects.create(
                user=user,
                weight_kg=bad_weight,
                measured_at=timezone.now(),
            )


@pytest.mark.django_db
def test_profile_get_and_patch_before_creation_return_404_profile_missing():
    user = User.objects.create_user("noprofile@example.test", PASSWORD)
    client = auth_csrf_client(user)

    get_resp = client.get(PROFILE_URL)
    assert get_resp.status_code == 404
    assert get_resp.data["error"]["code"] == "profile_missing"

    patch_resp = client.patch(
        PROFILE_URL,
        {"weight_kg": "70.0"},
        format="json",
        **csrf_header(client),
    )
    assert patch_resp.status_code == 404
    assert patch_resp.data["error"]["code"] == "profile_missing"


@pytest.mark.django_db
def test_profile_get_returns_current_profile_and_dynamic_age_in_kyiv(monkeypatch):
    create_time = datetime(2025, 5, 10, 12, 0, 0, tzinfo=dt_timezone.utc)
    monkeypatch.setattr(timezone, "now", lambda: create_time)

    user = User.objects.create_user("dynamic_age@example.test", PASSWORD)
    client = auth_csrf_client(user)

    post_resp = client.post(
        PROFILE_URL,
        valid_profile_payload(date_of_birth="2000-05-15"),
        format="json",
        **csrf_header(client),
    )
    assert post_resp.status_code == 201
    assert post_resp.data["age"] == 24

    # Advance time past birthday in 2026 in Europe/Kyiv (May 15 in Kyiv)
    read_time = datetime(2026, 5, 14, 21, 30, 0, tzinfo=dt_timezone.utc)
    monkeypatch.setattr(timezone, "now", lambda: read_time)
    client = auth_csrf_client(user)

    get_resp = client.get(PROFILE_URL)
    assert get_resp.status_code == 200
    assert get_resp.data["age"] == 26


@pytest.mark.django_db
def test_profile_patch_weight_change_vs_non_weight_and_unchanged_weight():
    user = User.objects.create_user("patch@example.test", PASSWORD)
    client = auth_csrf_client(user)

    client.post(
        PROFILE_URL,
        valid_profile_payload(
            first_name="Анна",
            last_name="Шевченко",
            weight_kg="68.4",
        ),
        format="json",
        **csrf_header(client),
    )
    assert WeightEntry.objects.filter(user=user).count() == 1

    # 1. Updating weight creates a new WeightEntry
    weight_resp = client.patch(
        PROFILE_URL,
        {"weight_kg": "67.9", "workouts_per_week": 4},
        format="json",
        **csrf_header(client),
    )
    assert weight_resp.status_code == 200
    assert weight_resp.data["weight_kg"] == "67.9"
    assert weight_resp.data["workouts_per_week"] == 4
    assert WeightEntry.objects.filter(user=user).count() == 2

    # 2. Updating non-weight fields (including clearing first/last name) does NOT
    # create WeightEntry
    non_weight_resp = client.patch(
        PROFILE_URL,
        {
            "first_name": "",
            "last_name": "",
            "height_cm": "172.5",
            "workouts_per_week": 5,
            "fitness_goal": "muscle_gain",
            "experience_level": "advanced",
            "gender": "other",
        },
        format="json",
        **csrf_header(client),
    )
    assert non_weight_resp.status_code == 200
    assert non_weight_resp.data["first_name"] == ""
    assert non_weight_resp.data["last_name"] == ""
    assert non_weight_resp.data["height_cm"] == "172.5"
    assert non_weight_resp.data["workouts_per_week"] == 5
    assert non_weight_resp.data["fitness_goal"] == "muscle_gain"
    assert non_weight_resp.data["experience_level"] == "advanced"
    assert non_weight_resp.data["gender"] == "other"
    assert WeightEntry.objects.filter(user=user).count() == 2

    # 3. Updating with unchanged weight ("67.9" -> "67.9") does NOT create a
    # duplicate WeightEntry
    unchanged_resp = client.patch(
        PROFILE_URL,
        {"weight_kg": "67.9"},
        format="json",
        **csrf_header(client),
    )
    assert unchanged_resp.status_code == 200
    assert WeightEntry.objects.filter(user=user).count() == 2

    # 4. Updating to 70.0 then sending "70" (equivalent Decimal) does NOT create a
    # duplicate WeightEntry
    to_70 = client.patch(
        PROFILE_URL,
        {"weight_kg": "70.0"},
        format="json",
        **csrf_header(client),
    )
    assert to_70.status_code == 200
    assert WeightEntry.objects.filter(user=user).count() == 3

    equiv_70 = client.patch(
        PROFILE_URL,
        {"weight_kg": "70"},
        format="json",
        **csrf_header(client),
    )
    assert equiv_70.status_code == 200
    assert equiv_70.data["weight_kg"] == "70.0"
    assert WeightEntry.objects.filter(user=user).count() == 3


@pytest.mark.django_db
def test_profile_patch_invalid_partial_update_and_atomic_rollback(monkeypatch):
    user = User.objects.create_user("atomic_patch@example.test", PASSWORD)
    client = auth_csrf_client(user)

    client.post(
        PROFILE_URL,
        valid_profile_payload(first_name="Олег", weight_kg="80.0"),
        format="json",
        **csrf_header(client),
    )

    # Invalid partial update: valid first_name + invalid weight_kg
    bad_resp = client.patch(
        PROFILE_URL,
        {"first_name": "Нове", "weight_kg": "10.0"},
        format="json",
        **csrf_header(client),
    )
    assert bad_resp.status_code == 400
    assert bad_resp.data["error"]["code"] == "validation_error"
    assert "weight_kg" in bad_resp.data["error"]["fields"]

    profile = Profile.objects.get(user=user)
    assert profile.first_name == "Олег"
    assert profile.weight_kg == Decimal("80.0")
    assert WeightEntry.objects.filter(user=user).count() == 1

    # Atomic rollback if WeightEntry.objects.create raises during PATCH
    def boom(*args, **kwargs):
        raise IntegrityError("Simulated WeightEntry failure on PATCH")

    monkeypatch.setattr(WeightEntry.objects, "create", boom)
    with pytest.raises(IntegrityError):
        client.patch(
            PROFILE_URL,
            {"first_name": "НеЗбережеться", "weight_kg": "79.0"},
            format="json",
            **csrf_header(client),
        )

    profile.refresh_from_db()
    assert profile.first_name == "Олег"
    assert profile.weight_kg == Decimal("80.0")
    assert WeightEntry.objects.filter(user=user).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "unknown_field,value",
    [
        ("age", 25),
        ("id", 1),
        ("user", 1),
        ("user_id", 1),
        ("created_at", "2026-01-01T00:00:00Z"),
        ("extra_field", "unexpected"),
    ],
)
def test_profile_rejects_writable_age_and_unknown_fields_on_post_and_patch(
    unknown_field, value
):
    user = User.objects.create_user(f"unknown_{unknown_field}@example.test", PASSWORD)
    client = auth_csrf_client(user)

    post_resp = client.post(
        PROFILE_URL,
        valid_profile_payload(**{unknown_field: value}),
        format="json",
        **csrf_header(client),
    )
    assert post_resp.status_code == 400
    assert post_resp.data["error"]["code"] == "unknown_field"
    assert unknown_field in post_resp.data["error"]["fields"]

    client.post(
        PROFILE_URL,
        valid_profile_payload(),
        format="json",
        **csrf_header(client),
    )

    patch_resp = client.patch(
        PROFILE_URL,
        {unknown_field: value},
        format="json",
        **csrf_header(client),
    )
    assert patch_resp.status_code == 400
    assert patch_resp.data["error"]["code"] == "unknown_field"
    assert unknown_field in patch_resp.data["error"]["fields"]


@pytest.mark.django_db
def test_profile_patch_date_of_birth_validated_against_profile_created_at(monkeypatch):
    # Profile created on 2020-05-10 in Europe/Kyiv
    created_at_2020 = datetime(2020, 5, 10, 9, 0, 0, tzinfo=dt_timezone.utc)
    monkeypatch.setattr(timezone, "now", lambda: created_at_2020)

    user = User.objects.create_user("dob_patch@example.test", PASSWORD)
    client = auth_csrf_client(user)

    # Born 1961-05-01 -> age 59 on 2020-05-10
    create_resp = client.post(
        PROFILE_URL,
        valid_profile_payload(date_of_birth="1961-05-01"),
        format="json",
        **csrf_header(client),
    )
    assert create_resp.status_code == 201
    assert create_resp.data["age"] == 59

    # Fast-forward to 2026-05-10 (user is now 65 today, > 59)
    now_2026 = datetime(2026, 5, 10, 9, 0, 0, tzinfo=dt_timezone.utc)
    monkeypatch.setattr(timezone, "now", lambda: now_2026)
    client = auth_csrf_client(user)

    # Correcting date_of_birth to 1960-05-11 (which was age 59 on 2020-05-10) succeeds
    # even though on 2026-05-10 the user is 65
    valid_correction = client.patch(
        PROFILE_URL,
        {"date_of_birth": "1960-05-11"},
        format="json",
        **csrf_header(client),
    )
    assert valid_correction.status_code == 200
    assert valid_correction.data["date_of_birth"] == "1960-05-11"
    assert valid_correction.data["age"] == 65

    # Date that was age 60 on 2020-05-10 (1960-05-10) is rejected
    too_old_on_creation = client.patch(
        PROFILE_URL,
        {"date_of_birth": "1960-05-10"},
        format="json",
        **csrf_header(client),
    )
    assert too_old_on_creation.status_code == 400
    assert too_old_on_creation.data["error"]["code"] == "validation_error"
    assert "date_of_birth" in too_old_on_creation.data["error"]["fields"]

    # Date that was age 18 on 2020-05-10 (2001-05-11) is rejected even though > 19
    # in 2026
    too_young_on_creation = client.patch(
        PROFILE_URL,
        {"date_of_birth": "2001-05-11"},
        format="json",
        **csrf_header(client),
    )
    assert too_young_on_creation.status_code == 400
    assert too_young_on_creation.data["error"]["code"] == "validation_error"
    assert "date_of_birth" in too_young_on_creation.data["error"]["fields"]


@pytest.mark.django_db(transaction=True)
def test_concurrent_weight_updates_serialize_and_record_both_entries():
    user = User.objects.create_user("concurrent_patch@example.test", PASSWORD)
    ProfileService.create_profile(
        user,
        {
            "date_of_birth": date(1995, 5, 14),
            "weight_kg": Decimal("70.0"),
            "height_cm": Decimal("175.0"),
            "gender": Gender.MALE,
            "fitness_goal": FitnessGoal.MAINTENANCE,
            "experience_level": ExperienceLevel.INTERMEDIATE,
            "workouts_per_week": 3,
        },
    )

    def update_worker(new_weight: Decimal):
        try:
            return ProfileService.update_profile(user, {"weight_kg": new_weight})
        finally:
            connection.close()
            connections.close_all()

    weights = [Decimal("71.0"), Decimal("72.5")]
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(update_worker, w) for w in weights]
        for f in futures:
            f.result()

    entries = list(
        WeightEntry.objects.filter(user=user).order_by("-measured_at", "-id")
    )
    assert len(entries) == 3
    recorded_weights = {e.weight_kg for e in entries}
    assert recorded_weights == {Decimal("70.0"), Decimal("71.0"), Decimal("72.5")}

    profile = Profile.objects.get(user=user)
    assert profile.weight_kg == entries[0].weight_kg


@pytest.mark.django_db
def test_weight_entries_ordering_and_tie_breaking_by_id_desc():
    user = User.objects.create_user("ordering@example.test", PASSWORD)
    client = auth_csrf_client(user)

    t1 = datetime(2026, 3, 1, 10, 0, 0, tzinfo=dt_timezone.utc)
    t2 = datetime(2026, 3, 2, 10, 0, 0, tzinfo=dt_timezone.utc)

    e1 = WeightEntry.objects.create(
        user=user, weight_kg=Decimal("70.0"), measured_at=t1
    )
    # Two entries with the exact same measured_at timestamp t2
    e2_first = WeightEntry.objects.create(
        user=user, weight_kg=Decimal("71.0"), measured_at=t2
    )
    e2_second = WeightEntry.objects.create(
        user=user, weight_kg=Decimal("71.5"), measured_at=t2
    )

    response = client.get(WEIGHT_ENTRIES_URL)
    assert response.status_code == 200
    assert response.data["count"] == 3
    results = response.data["results"]
    assert [item["id"] for item in results] == [e2_second.id, e2_first.id, e1.id]
    assert results[0] == {
        "id": e2_second.id,
        "measured_at": "2026-03-02T10:00:00Z",
        "weight_kg": "71.5",
    }


@pytest.mark.django_db
def test_weight_entries_owner_isolation():
    user_a = User.objects.create_user("usera@example.test", PASSWORD)
    user_b = User.objects.create_user("userb@example.test", PASSWORD)

    client_a = auth_csrf_client(user_a)
    client_b = auth_csrf_client(user_b)

    client_a.post(
        PROFILE_URL,
        valid_profile_payload(weight_kg="80.0"),
        format="json",
        **csrf_header(client_a),
    )
    client_b.post(
        PROFILE_URL,
        valid_profile_payload(weight_kg="60.5"),
        format="json",
        **csrf_header(client_b),
    )

    resp_b = client_b.get(WEIGHT_ENTRIES_URL)
    assert resp_b.status_code == 200
    assert resp_b.data["count"] == 1
    assert resp_b.data["results"][0]["weight_kg"] == "60.5"
    user_a_ids = set(
        WeightEntry.objects.filter(user=user_a).values_list("id", flat=True)
    )
    assert all(item["id"] not in user_a_ids for item in resp_b.data["results"])


@pytest.mark.django_db
def test_weight_entries_date_filter_validation_and_unknown_query_params():
    user = User.objects.create_user("filter_val@example.test", PASSWORD)
    client = auth_csrf_client(user)

    # Single start_date without end_date
    r1 = client.get(f"{WEIGHT_ENTRIES_URL}?start_date=2026-03-01")
    assert r1.status_code == 400
    assert r1.data["error"]["code"] == "validation_error"
    assert "end_date" in r1.data["error"]["fields"]

    # Single end_date without start_date
    r2 = client.get(f"{WEIGHT_ENTRIES_URL}?end_date=2026-03-10")
    assert r2.status_code == 400
    assert r2.data["error"]["code"] == "validation_error"
    assert "start_date" in r2.data["error"]["fields"]

    # start_date == end_date and start_date > end_date
    for query in (
        "start_date=2026-03-10&end_date=2026-03-10",
        "start_date=2026-03-11&end_date=2026-03-10",
    ):
        r3 = client.get(f"{WEIGHT_ENTRIES_URL}?{query}")
        assert r3.status_code == 400
        assert r3.data["error"]["code"] == "validation_error"
        assert "end_date" in r3.data["error"]["fields"]

    # Unknown query parameter
    r4 = client.get(f"{WEIGHT_ENTRIES_URL}?foo=bar")
    assert r4.status_code == 400
    assert r4.data["error"]["code"] == "unknown_field"
    assert "foo" in r4.data["error"]["fields"]


@pytest.mark.django_db
def test_weight_entries_kyiv_dst_spring_forward_and_fall_back_boundaries():
    user = User.objects.create_user("dst@example.test", PASSWORD)
    client = auth_csrf_client(user)

    # Spring-forward: 2026-03-29 (Europe/Kyiv switches UTC+2 -> UTC+3)
    # 2026-03-29T00:00:00+02:00 == 2026-03-28T22:00:00Z
    # 2026-03-30T00:00:00+03:00 == 2026-03-29T21:00:00Z
    sf_before = WeightEntry.objects.create(
        user=user,
        weight_kg=Decimal("70.0"),
        measured_at=datetime(2026, 3, 28, 21, 59, 59, tzinfo=dt_timezone.utc),
    )
    sf_start = WeightEntry.objects.create(
        user=user,
        weight_kg=Decimal("70.1"),
        measured_at=datetime(2026, 3, 28, 22, 0, 0, tzinfo=dt_timezone.utc),
    )
    sf_end_inside = WeightEntry.objects.create(
        user=user,
        weight_kg=Decimal("70.2"),
        measured_at=datetime(2026, 3, 29, 20, 59, 59, tzinfo=dt_timezone.utc),
    )
    sf_after = WeightEntry.objects.create(
        user=user,
        weight_kg=Decimal("70.3"),
        measured_at=datetime(2026, 3, 29, 21, 0, 0, tzinfo=dt_timezone.utc),
    )

    sf_resp = client.get(
        f"{WEIGHT_ENTRIES_URL}?start_date=2026-03-29&end_date=2026-03-30"
    )
    assert sf_resp.status_code == 200
    sf_ids = [item["id"] for item in sf_resp.data["results"]]
    assert sf_ids == [sf_end_inside.id, sf_start.id]
    assert sf_before.id not in sf_ids
    assert sf_after.id not in sf_ids

    # Fall-back: 2026-10-25 (Europe/Kyiv switches UTC+3 -> UTC+2)
    # 2026-10-25T00:00:00+03:00 == 2026-10-24T21:00:00Z
    # 2026-10-26T00:00:00+02:00 == 2026-10-25T22:00:00Z
    fb_before = WeightEntry.objects.create(
        user=user,
        weight_kg=Decimal("71.0"),
        measured_at=datetime(2026, 10, 24, 20, 59, 59, tzinfo=dt_timezone.utc),
    )
    fb_start = WeightEntry.objects.create(
        user=user,
        weight_kg=Decimal("71.1"),
        measured_at=datetime(2026, 10, 24, 21, 0, 0, tzinfo=dt_timezone.utc),
    )
    fb_end_inside = WeightEntry.objects.create(
        user=user,
        weight_kg=Decimal("71.2"),
        measured_at=datetime(2026, 10, 25, 21, 59, 59, tzinfo=dt_timezone.utc),
    )
    fb_after = WeightEntry.objects.create(
        user=user,
        weight_kg=Decimal("71.3"),
        measured_at=datetime(2026, 10, 25, 22, 0, 0, tzinfo=dt_timezone.utc),
    )

    fb_resp = client.get(
        f"{WEIGHT_ENTRIES_URL}?start_date=2026-10-25&end_date=2026-10-26"
    )
    assert fb_resp.status_code == 200
    fb_ids = [item["id"] for item in fb_resp.data["results"]]
    assert fb_ids == [fb_end_inside.id, fb_start.id]
    assert fb_before.id not in fb_ids
    assert fb_after.id not in fb_ids


@pytest.mark.django_db
def test_weight_entries_pagination_and_edge_cases():
    user = User.objects.create_user("pagination@example.test", PASSWORD)
    client = auth_csrf_client(user)

    # Empty result on page=1 before profile creation
    empty_p1 = client.get(WEIGHT_ENTRIES_URL)
    assert empty_p1.status_code == 200
    assert empty_p1.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }

    # Out-of-range page=2 when count == 0
    empty_p2 = client.get(f"{WEIGHT_ENTRIES_URL}?page=2")
    assert empty_p2.status_code == 400
    assert empty_p2.data["error"]["code"] == "validation_error"
    assert "page" in empty_p2.data["error"]["fields"]

    # Create 3 entries
    for idx in range(3):
        WeightEntry.objects.create(
            user=user,
            weight_kg=Decimal(f"7{idx}.0"),
            measured_at=datetime(2026, 4, idx + 1, 12, 0, 0, tzinfo=dt_timezone.utc),
        )

    # Page 1 of 2 (page_size=2)
    p1 = client.get(f"{WEIGHT_ENTRIES_URL}?page=1&page_size=2")
    assert p1.status_code == 200
    assert p1.data["count"] == 3
    assert len(p1.data["results"]) == 2
    assert p1.data["previous"] is None
    assert "page=2" in p1.data["next"]
    assert "page_size=2" in p1.data["next"]

    # Page 2 of 2 (page_size=2)
    p2 = client.get(f"{WEIGHT_ENTRIES_URL}?page=2&page_size=2")
    assert p2.status_code == 200
    assert p2.data["count"] == 3
    assert len(p2.data["results"]) == 1
    assert p2.data["next"] is None
    assert "page=1" in p2.data["previous"]

    # Out-of-range page=3 when only 2 pages exist
    p3 = client.get(f"{WEIGHT_ENTRIES_URL}?page=3&page_size=2")
    assert p3.status_code == 400
    assert p3.data["error"]["code"] == "validation_error"
    assert "page" in p3.data["error"]["fields"]

    # Invalid page values
    for bad_page in ("0", "-1", "abc"):
        resp = client.get(f"{WEIGHT_ENTRIES_URL}?page={bad_page}")
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "validation_error"
        assert "page" in resp.data["error"]["fields"]

    # Invalid page_size values
    for bad_size in ("0", "101", "abc"):
        resp = client.get(f"{WEIGHT_ENTRIES_URL}?page_size={bad_size}")
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "validation_error"
        assert "page_size" in resp.data["error"]["fields"]


@pytest.mark.django_db
def test_weight_entries_read_only_enforcement():
    user = User.objects.create_user("readonly@example.test", PASSWORD)
    client = auth_csrf_client(user)

    for method in ("post", "patch", "put", "delete"):
        caller = getattr(client, method)
        resp = caller(
            WEIGHT_ENTRIES_URL,
            {"weight_kg": "70.0"},
            format="json",
            **csrf_header(client),
        )
        assert resp.status_code == 405

    detail_resp = client.get(f"{WEIGHT_ENTRIES_URL}1/")
    assert detail_resp.status_code == 404


@pytest.mark.django_db
def test_profile_and_weight_entries_security_csrf_isolation_and_admin_boundary():
    # 1. Unauthenticated access returns 401 authentication_required with
    # WWW-Authenticate: Session
    anon = csrf_client()
    for method, url, payload in (
        ("get", PROFILE_URL, None),
        ("post", PROFILE_URL, valid_profile_payload()),
        ("patch", PROFILE_URL, {"weight_kg": "70.0"}),
        ("get", WEIGHT_ENTRIES_URL, None),
    ):
        caller = getattr(anon, method)
        kwargs = (
            {"data": payload, "format": "json", **csrf_header(anon)}
            if payload is not None
            else {}
        )
        resp = caller(url, **kwargs)
        assert resp.status_code == 401
        assert resp.data["error"]["code"] == "authentication_required"
        assert resp["WWW-Authenticate"] == 'Session realm="api"'

    # 2. Missing or invalid CSRF token on POST / PATCH /api/v1/profile/ returns
    # 403 csrf_failed
    user_a = User.objects.create_user("seca@example.test", PASSWORD)
    user_b = User.objects.create_user("secb@example.test", PASSWORD)
    client_a = auth_csrf_client(user_a)
    client_b = auth_csrf_client(user_b)

    no_csrf_post = client_a.post(PROFILE_URL, valid_profile_payload(), format="json")
    assert no_csrf_post.status_code == 403
    assert no_csrf_post.json()["error"]["code"] == "csrf_failed"

    bad_csrf_post = client_a.post(
        PROFILE_URL,
        valid_profile_payload(),
        format="json",
        HTTP_X_CSRFTOKEN="invalid-token-value",
    )
    assert bad_csrf_post.status_code == 403
    assert bad_csrf_post.json()["error"]["code"] == "csrf_failed"

    # Create User A's profile with valid CSRF
    created_a = client_a.post(
        PROFILE_URL,
        valid_profile_payload(first_name="Аліса", weight_kg="65.0"),
        format="json",
        **csrf_header(client_a),
    )
    assert created_a.status_code == 201

    no_csrf_patch = client_a.patch(PROFILE_URL, {"weight_kg": "64.0"}, format="json")
    assert no_csrf_patch.status_code == 403
    assert no_csrf_patch.json()["error"]["code"] == "csrf_failed"

    # 3. Cross-user isolation: User B cannot read or overwrite User A's profile
    assert client_b.get(PROFILE_URL).status_code == 404
    assert (
        client_b.patch(
            PROFILE_URL,
            {"first_name": "Хакер"},
            format="json",
            **csrf_header(client_b),
        ).status_code
        == 404
    )
    assert Profile.objects.get(user=user_a).first_name == "Аліса"

    # 4. Deactivating User A invalidates session access to P01-P04
    user_a.is_active = False
    user_a.save(update_fields=["is_active"])

    assert client_a.get(PROFILE_URL).status_code == 401
    assert (
        client_a.post(
            PROFILE_URL,
            valid_profile_payload(),
            format="json",
            **csrf_header(client_a),
        ).status_code
        == 401
    )
    assert (
        client_a.patch(
            PROFILE_URL,
            {"weight_kg": "64.0"},
            format="json",
            **csrf_header(client_a),
        ).status_code
        == 401
    )
    assert client_a.get(WEIGHT_ENTRIES_URL).status_code == 401

    # 5. Django Admin boundary (BR-028): Profile and WeightEntry not registered
    assert Profile not in admin.site._registry
    assert WeightEntry not in admin.site._registry
