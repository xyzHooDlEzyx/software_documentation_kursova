"""Rate-limiting throttles for authentication and password recovery endpoints."""

import hashlib

from rest_framework.exceptions import ParseError
from rest_framework.throttling import SimpleRateThrottle


class PasswordResetIPThrottle(SimpleRateThrottle):
    """Limits password reset requests per client IP address."""

    scope = "password_reset_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class PasswordResetEmailThrottle(SimpleRateThrottle):
    """Limits password reset requests per normalized target email address.

    Applies identically to existing and non-existing email addresses to prevent
    account enumeration via rate-limit timing or status differences.
    """

    scope = "password_reset_email"

    def get_cache_key(self, request, view):
        try:
            data = request.data
        except ParseError, Exception:
            return None

        email = data.get("email") if isinstance(data, dict) else None
        if not isinstance(email, str):
            return None

        normalized = email.strip().lower()
        if not normalized or "@" not in normalized:
            return None

        local_part, _, domain_part = normalized.partition("@")
        if not local_part or not domain_part or "@" in domain_part:
            return None

        ident = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class PasswordResetConfirmIPThrottle(SimpleRateThrottle):
    """Limits password reset confirmation attempts per client IP address."""

    scope = "password_reset_confirm_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
