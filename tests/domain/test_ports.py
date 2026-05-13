from briefing.domain.ports import (
    ArticleRepository,
    KeywordExtractor,
    SourceAdapter,
    VaultPublisher,
    VaultSync,
)


def test_ports_are_protocols():
    class Dummy:
        pass

    assert isinstance(Dummy(), SourceAdapter) is False
    assert isinstance(Dummy(), KeywordExtractor) is False
    assert isinstance(Dummy(), ArticleRepository) is False
    assert isinstance(Dummy(), VaultPublisher) is False
    assert isinstance(Dummy(), VaultSync) is False
