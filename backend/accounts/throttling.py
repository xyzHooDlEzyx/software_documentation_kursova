"""Rate-limiting throttles for authentication and password recovery endpoints.

Client IP comes from DRF ``get_ident``; ``REST_FRAMEWORK["NUM_PROXIES"]`` must
match the real proxy chain, otherwise a spoofed ``X-Forwarded-For`` would let a
client pick its own throttle key.
"""

import hashlib

from rest_framework.throttling import SimpleRateThrottle


def normalized_email_ident(request) -> str | None:
    """Return a hashed, normalized email from the request body, if well-formed."""
    # A ParseError propagates on purpose: DRF replaces unparsable bodies with
    # empty data, so swallowing it here would turn ``invalid_json`` into a
    # misleading ``validation_error``.
    data = request.data
    email = data.get("email") if isinstance(data, dict) else None
    if not isinstance(email, str):
        return None

    normalized = email.strip().lower()
    local_part, at, domain_part = normalized.partition("@")
    if not at or not local_part or not domain_part or "@" in domain_part:
        return None

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class IPRateThrottle(SimpleRateThrottle):
    """Base throttle keyed by client IP address."""

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class EmailRateThrottle(SimpleRateThrottle):
    """Base throttle keyed by the normalized target email address.

    Applies identically to existing and non-existing addresses so the limit
    does not reveal whether an account exists.
    """

    def get_cache_key(self, request, view):
        ident = normalized_email_ident(request)
        if ident is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}


class LoginIPThrottle(IPRateThrottle):
    """Limits login attempts per client IP address."""

    scope = "login_ip"


class LoginEmailThrottle(EmailRateThrottle):
    """Limits login attempts per target account email (password guessing)."""

    scope = "login_email"


class RegisterIPThrottle(IPRateThrottle):
    """Limits account registrations per client IP address."""

    scope = "register_ip"


class PasswordResetIPThrottle(IPRateThrottle):
    """Limits password reset requests per client IP address."""

    scope = "password_reset_ip"


class PasswordResetEmailThrottle(EmailRateThrottle):
    """Limits password reset requests per normalized target email address."""

    scope = "password_reset_email"


class PasswordResetConfirmIPThrottle(IPRateThrottle):
    """Limits password reset confirmation attempts per client IP address."""

    scope = "password_reset_confirm_ip"
