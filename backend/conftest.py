import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _isolate_rate_limit_cache():
    """Throttle counters live in the cache; never let them leak between tests."""
    cache.clear()
    yield
    cache.clear()
