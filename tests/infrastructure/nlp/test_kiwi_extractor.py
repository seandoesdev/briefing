from pathlib import Path

from briefing.infrastructure.nlp.kiwi_extractor import KiwiKeywordExtractor


STOPWORDS = Path("data/stopwords.txt")


def test_extract_korean_nouns():
    ex = KiwiKeywordExtractor(stopwords_path=STOPWORDS, top_n=5)
    tags = ex.extract("네이버가 새로운 AI 반도체를 발표했다. 인공지능 시장 경쟁이 치열하다.")
    assert "네이버" in tags
    assert "반도체" in tags
    assert "것" not in tags


def test_extract_empty_text_returns_empty():
    ex = KiwiKeywordExtractor(stopwords_path=STOPWORDS, top_n=5)
    assert ex.extract("") == []


def test_extract_respects_top_n():
    ex = KiwiKeywordExtractor(stopwords_path=STOPWORDS, top_n=2)
    tags = ex.extract("네이버 카카오 삼성 LG SK 현대 두산")
    assert len(tags) <= 2
