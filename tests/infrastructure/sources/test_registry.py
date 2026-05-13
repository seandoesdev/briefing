import pytest

from briefing.domain.value_objects import SourceName
from briefing.infrastructure.sources.dooray import DoorayAdapter
from briefing.infrastructure.sources.registry import SourceRegistry


def test_register_and_get():
    r = SourceRegistry()
    r.register(DoorayAdapter(token=None))
    got = r.get(SourceName("dooray"))
    assert got is not None
    assert got.name == "dooray"


def test_get_unknown_returns_none():
    r = SourceRegistry()
    assert r.get(SourceName("unknown")) is None


def test_register_duplicate_raises():
    r = SourceRegistry()
    r.register(DoorayAdapter(token=None))
    with pytest.raises(ValueError):
        r.register(DoorayAdapter(token=None))
