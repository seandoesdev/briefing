from briefing.domain.value_objects import SourceName
from briefing.infrastructure.sources.dooray import DoorayAdapter


def test_parse_simple_text():
    a = DoorayAdapter(token=None).parse({"text": "안녕하세요 두레이 메시지입니다."})
    assert a.source == SourceName("dooray")
    assert a.body.startswith("안녕하세요")
    # Title comes from first line (up to 60 chars) when no explicit title
    assert "안녕하세요" in a.title
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


def test_parse_attachment_fields_included_in_body():
    payload = {
        "attachments": [
            {
                "title": "T",
                "fields": [
                    {"title": "Author", "value": "alice"},
                    {"title": "Tag", "value": "release"},
                ],
            }
        ],
    }
    a = DoorayAdapter(token=None).parse(payload)
    assert "alice" in a.body
    assert "release" in a.body


def test_parse_message_object_shape():
    payload = {"message": {"subject": "보고서", "text": "월간 보고서 본문"}}
    a = DoorayAdapter(token=None).parse(payload)
    assert a.title == "보고서"
    assert "월간 보고서" in a.body


def test_parse_subject_and_content_shape():
    payload = {"subject": "공지", "content": "내용 본문"}
    a = DoorayAdapter(token=None).parse(payload)
    assert a.title == "공지"
    assert "내용 본문" in a.body


def test_parse_unrecognized_shape_falls_back_to_raw_json():
    payload = {"weird_field": "x", "another": [1, 2, 3]}
    a = DoorayAdapter(token=None).parse(payload)
    # body 에 원본 JSON 이 들어가야 사용자가 admin 에서 확인 가능
    assert "weird_field" in a.body
    assert a.title != ""  # 어떻게든 title 생성


def test_parse_never_raises_on_empty():
    a = DoorayAdapter(token=None).parse({})
    assert a.title  # non-empty
    assert a.payload_hash


def test_verify_without_token_always_true():
    assert DoorayAdapter(token=None).verify({}, b"")


def test_verify_with_token_checks_header():
    ad = DoorayAdapter(token="s3cret")
    assert ad.verify({"X-Dooray-Token": "s3cret"}, b"") is True
    assert ad.verify({"X-Dooray-Token": "wrong"}, b"") is False
    assert ad.verify({}, b"") is False


def test_verify_with_token_is_case_insensitive():
    ad = DoorayAdapter(token="s3cret")
    assert ad.verify({"x-dooray-token": "s3cret"}, b"") is True
    assert ad.verify({"X-DOORAY-TOKEN": "s3cret"}, b"") is True
