from briefing.domain.value_objects import SourceName
from briefing.infrastructure.sources.dooray import DoorayAdapter


def test_parse_simple_text():
    a = DoorayAdapter(token=None).parse({"text": "안녕하세요 두레이 메시지입니다."})
    assert a.source == SourceName("dooray")
    assert a.body.startswith("안녕하세요")
    assert a.title == a.body[:40]
    assert a.url is None
    assert a.payload_hash


def test_parse_with_attachments():
    payload = {
        "text": "헤더",
        "attachments": [
            {
                "title": "기사 제목",
                "titleLink": "https://example.com/x",
                "text": "기사 본문",
            }
        ],
    }
    a = DoorayAdapter(token=None).parse(payload)
    assert a.title == "기사 제목"
    assert a.url == "https://example.com/x"
    assert "기사 본문" in a.body


def test_verify_without_token_always_true():
    assert DoorayAdapter(token=None).verify({}, b"")


def test_verify_with_token_checks_header():
    ad = DoorayAdapter(token="s3cret")
    assert ad.verify({"X-Dooray-Token": "s3cret"}, b"") is True
    assert ad.verify({"X-Dooray-Token": "wrong"}, b"") is False
    assert ad.verify({}, b"") is False
