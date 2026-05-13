from __future__ import annotations

from collections import Counter
from pathlib import Path

from kiwipiepy import Kiwi

from briefing.domain.value_objects import Tag


class KiwiKeywordExtractor:
    """한국어 형태소 분석 기반 키워드 추출."""

    _NOUN_TAGS = {"NNG", "NNP", "SL"}  # 일반/고유명사 + 외국어

    def __init__(self, *, stopwords_path: Path | None = None, top_n: int = 5) -> None:
        self._kiwi = Kiwi()
        self._top_n = top_n
        self._stopwords = self._load_stopwords(stopwords_path)

    @staticmethod
    def _load_stopwords(path: Path | None) -> set[str]:
        if not path or not Path(path).exists():
            return set()
        words: set[str] = set()
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            words.add(line)
        return words

    def extract(self, text: str) -> list[Tag]:
        if not text:
            return []
        tokens = self._kiwi.tokenize(text)
        counter: Counter[str] = Counter()
        for tok in tokens:
            if tok.tag not in self._NOUN_TAGS:
                continue
            form = tok.form.strip()
            if len(form) < 2:
                continue
            if form in self._stopwords:
                continue
            counter[form] += 1
        return [Tag(w) for w, _ in counter.most_common(self._top_n)]
