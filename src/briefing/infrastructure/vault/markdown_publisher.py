from __future__ import annotations

from pathlib import Path

from briefing.domain.entities import Article


class MarkdownVaultPublisher:
    """vault/<source>/<YYYY-MM-DD>.md 파일에 append 방식으로 기록."""

    def __init__(self, vault_root: Path) -> None:
        self._vault_root = Path(vault_root)

    def publish(self, article: Article) -> Path:
        local_dt = article.received_at
        day = local_dt.date().isoformat()
        folder = self._vault_root / str(article.source)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{day}.md"

        block = self._render_block(article)

        if path.exists():
            with path.open("a", encoding="utf-8") as f:
                f.write(block)
        else:
            with path.open("w", encoding="utf-8") as f:
                f.write(f"# {day}\n\n")
                f.write(block)
        return path

    @staticmethod
    def _render_block(article: Article) -> str:
        time_part = article.received_at.strftime("%H:%M")
        tags_part = " ".join(f"#{t}" for t in article.tags) if article.tags else "(none)"
        lines = [
            f"## {time_part} — {article.title}",
            f"**source**: {article.source} · **tags**: {tags_part}",
        ]
        if article.url:
            lines.append(f"**url**: {article.url}")
        lines.append("")
        lines.append(article.body.rstrip())
        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines) + "\n"
