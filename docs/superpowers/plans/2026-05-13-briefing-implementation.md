# Briefing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dooray incoming webhook으로 수신된 메시지를 한국어 키워드 태깅과 함께 옵시디언 볼트 markdown으로 적재하고, git push로 로컬 볼트에 동기화하며, FastAPI 기반 admin UI로 관리할 수 있는 서비스를 구현한다.

**Architecture:** DDD 4-layer (domain → application → infrastructure → interface) + 포트/어댑터 패턴. 인-프로세스 asyncio worker + SQLite를 큐 겸 영속 저장소로 사용. Jinja2+HTMX 기반 admin UI. 신규 source는 `SourceAdapter` 구현 후 `SourceRegistry`에 등록만 하면 됨.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, Jinja2, pydantic / pydantic-settings, SQLite (stdlib), kiwipiepy, GitPython, pytest, httpx (test client).

**Reference spec:** `docs/superpowers/specs/2026-05-13-briefing-design.md`

**Path convention:** 모든 경로는 프로젝트 루트(`E:/private-projects/getNews`, 추후 `briefing`로 리네임)를 기준으로 한 상대경로.

**Shell convention:** Windows PowerShell. 모든 명령은 PowerShell에서 실행 가능한 형태로 기재. 패키지 매니저는 `pip` 가정. `uv` 사용 시 `pip install` → `uv pip install`로 치환.

---

## Phase 0: Bootstrap

### Task 0.1: Git 초기화 + .gitignore + 기본 README

**Files:**
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Git 저장소 초기화**

```powershell
git init
git branch -M main
```

- [ ] **Step 2: `.gitignore` 작성**

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
.venv/
venv/

# Briefing runtime artifacts
data/briefing.db
data/briefing.log
data/briefing.log.*

# Vault working copy (별도 git repo로 관리되는 영역)
vault/

# Editors / OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# Environment
.env
.env.local
```

- [ ] **Step 3: `README.md` 초안 작성**

```markdown
# Briefing

Dooray incoming webhook → Korean keyword tagging → Obsidian vault markdown.

See `docs/superpowers/specs/2026-05-13-briefing-design.md` for full design.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env  # then edit
uvicorn briefing.interface.app:create_app --factory --reload
```

## Layout

- `src/briefing/domain/` — pure domain (entities, value objects, ports)
- `src/briefing/application/` — use cases
- `src/briefing/infrastructure/` — concrete adapters (sqlite, kiwi, git, dooray)
- `src/briefing/interface/` — FastAPI app + admin UI
- `src/briefing/worker/` — background asyncio worker
```

- [ ] **Step 4: Commit**

```powershell
git add .gitignore README.md
git commit -m "chore: bootstrap repo (gitignore, readme)"
```

---

### Task 0.2: pyproject.toml + 패키지 골격

**Files:**
- Create: `pyproject.toml`
- Create: `src/briefing/__init__.py`
- Create: `src/briefing/domain/__init__.py`
- Create: `src/briefing/application/__init__.py`
- Create: `src/briefing/infrastructure/__init__.py`
- Create: `src/briefing/infrastructure/sources/__init__.py`
- Create: `src/briefing/infrastructure/persistence/__init__.py`
- Create: `src/briefing/infrastructure/nlp/__init__.py`
- Create: `src/briefing/infrastructure/vault/__init__.py`
- Create: `src/briefing/infrastructure/sync/__init__.py`
- Create: `src/briefing/interface/__init__.py`
- Create: `src/briefing/interface/webhook/__init__.py`
- Create: `src/briefing/interface/admin/__init__.py`
- Create: `src/briefing/worker/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: `pyproject.toml` 작성**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "briefing"
version = "0.1.0"
description = "Dooray webhook to Obsidian vault auto-ingestion service"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "kiwipiepy>=0.17",
    "GitPython>=3.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "ruff>=0.4",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: 패키지 빈 `__init__.py` 일괄 생성**

PowerShell:
```powershell
$paths = @(
  "src/briefing",
  "src/briefing/domain",
  "src/briefing/application",
  "src/briefing/infrastructure",
  "src/briefing/infrastructure/sources",
  "src/briefing/infrastructure/persistence",
  "src/briefing/infrastructure/nlp",
  "src/briefing/infrastructure/vault",
  "src/briefing/infrastructure/sync",
  "src/briefing/interface",
  "src/briefing/interface/webhook",
  "src/briefing/interface/admin",
  "src/briefing/worker",
  "tests"
)
foreach ($p in $paths) {
  New-Item -ItemType Directory -Force -Path $p | Out-Null
  if (-not (Test-Path "$p/__init__.py")) { New-Item -ItemType File -Path "$p/__init__.py" | Out-Null }
}
```

- [ ] **Step 3: 가상환경 + 설치 검증**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -c "import briefing; print('ok')"
```

Expected: `ok` 출력.

- [ ] **Step 4: Commit**

```powershell
git add pyproject.toml src/briefing tests
git commit -m "chore: project skeleton (pyproject, package layout)"
```

---

### Task 0.3: pytest 동작 확인용 스모크 테스트

**Files:**
- Create: `tests/test_smoke.py`

- [ ] **Step 1: 스모크 테스트 작성**

```python
# tests/test_smoke.py
import briefing


def test_package_imports():
    assert briefing is not None
```

- [ ] **Step 2: 실행 확인**

```powershell
pytest -v
```

Expected: 1 passed.

- [ ] **Step 3: Commit**

```powershell
git add tests/test_smoke.py
git commit -m "test: package import smoke"
```

---

## Phase 1: Domain Layer

### Task 1.1: Value Objects + ArticleStatus

**Files:**
- Create: `src/briefing/domain/value_objects.py`
- Create: `tests/domain/__init__.py`
- Create: `tests/domain/test_value_objects.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/domain/test_value_objects.py
from briefing.domain.value_objects import (
    ArticleStatus,
    payload_hash,
)


def test_article_status_values():
    assert ArticleStatus.RECEIVED.value == "received"
    assert ArticleStatus.PROCESSED.value == "processed"
    assert ArticleStatus.PUBLISHED.value == "published"
    assert ArticleStatus.FAILED.value == "failed"


def test_payload_hash_is_deterministic():
    p1 = {"a": 1, "b": [2, 3]}
    p2 = {"b": [2, 3], "a": 1}
    assert payload_hash(p1) == payload_hash(p2)
    assert len(payload_hash(p1)) == 64  # SHA-256 hex
```

- [ ] **Step 2: 테스트 실패 확인**

```powershell
pytest tests/domain/test_value_objects.py -v
```

Expected: ImportError or ModuleNotFoundError.

- [ ] **Step 3: 구현**

```python
# src/briefing/domain/value_objects.py
from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import NewType

SourceName = NewType("SourceName", str)
PayloadHash = NewType("PayloadHash", str)
ArticleId = NewType("ArticleId", str)
Tag = NewType("Tag", str)


class ArticleStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    PUBLISHED = "published"
    FAILED = "failed"


def payload_hash(payload: dict) -> PayloadHash:
    """Deterministic SHA-256 hex digest of a JSON-serialisable payload."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return PayloadHash(hashlib.sha256(canonical).hexdigest())
```

- [ ] **Step 4: 테스트 통과 확인**

```powershell
pytest tests/domain/test_value_objects.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/domain/value_objects.py tests/domain
git commit -m "feat(domain): value objects and ArticleStatus"
```

---

### Task 1.2: Article 엔티티

**Files:**
- Create: `src/briefing/domain/entities.py`
- Create: `tests/domain/test_entities.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/domain/test_entities.py
from datetime import datetime, timezone

from briefing.domain.entities import Article
from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
)


def _article(**overrides):
    base = dict(
        id=ArticleId("11111111-1111-1111-1111-111111111111"),
        source=SourceName("dooray"),
        external_id=None,
        payload_hash=PayloadHash("a" * 64),
        received_at=datetime(2026, 5, 13, 14, 32, tzinfo=timezone.utc),
        title="제목",
        body="본문",
        url=None,
        tags=[],
        raw_payload={"text": "본문"},
        status=ArticleStatus.RECEIVED,
        output_path=None,
        error=None,
        retry_count=0,
    )
    base.update(overrides)
    return Article(**base)


def test_article_default_status_received():
    a = _article()
    assert a.status is ArticleStatus.RECEIVED


def test_article_with_tags():
    a = _article(tags=[Tag("AI"), Tag("반도체")])
    assert "AI" in a.tags
```

- [ ] **Step 2: 테스트 실패 확인**

```powershell
pytest tests/domain/test_entities.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/domain/entities.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
)


@dataclass
class Article:
    id: ArticleId
    source: SourceName
    external_id: str | None
    payload_hash: PayloadHash
    received_at: datetime
    title: str
    body: str
    url: str | None
    tags: list[Tag]
    raw_payload: dict
    status: ArticleStatus = ArticleStatus.RECEIVED
    output_path: Path | None = None
    error: str | None = None
    retry_count: int = 0
    processed_at: datetime | None = None
    published_at: datetime | None = None

    def with_status(
        self,
        status: ArticleStatus,
        *,
        output_path: Path | None = None,
        error: str | None = None,
        processed_at: datetime | None = None,
        published_at: datetime | None = None,
    ) -> "Article":
        return Article(
            id=self.id,
            source=self.source,
            external_id=self.external_id,
            payload_hash=self.payload_hash,
            received_at=self.received_at,
            title=self.title,
            body=self.body,
            url=self.url,
            tags=list(self.tags),
            raw_payload=dict(self.raw_payload),
            status=status,
            output_path=output_path or self.output_path,
            error=error if error is not None else self.error,
            retry_count=self.retry_count,
            processed_at=processed_at or self.processed_at,
            published_at=published_at or self.published_at,
        )
```

- [ ] **Step 4: 테스트 통과 확인**

```powershell
pytest tests/domain/test_entities.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/domain/entities.py tests/domain/test_entities.py
git commit -m "feat(domain): Article entity"
```

---

### Task 1.3: Result 객체 (SyncResult, SyncStatus, AdminFilter)

**Files:**
- Create: `src/briefing/domain/results.py`
- Create: `tests/domain/test_results.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/domain/test_results.py
from datetime import datetime, timezone

from briefing.domain.results import AdminFilter, SyncResult, SyncStatus


def test_sync_result_success_factory():
    r = SyncResult.success(commit_sha="abc123", article_count=5)
    assert r.ok is True
    assert r.commit_sha == "abc123"
    assert r.error is None


def test_sync_result_failure_factory():
    r = SyncResult.failure(error="auth denied")
    assert r.ok is False
    assert r.error == "auth denied"


def test_admin_filter_defaults():
    f = AdminFilter()
    assert f.source is None
    assert f.status is None
    assert f.limit == 50
    assert f.offset == 0


def test_sync_status_dataclass():
    s = SyncStatus(
        last_push_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
        last_commit_sha="abc",
        pending_count=0,
        last_error=None,
    )
    assert s.pending_count == 0
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/domain/test_results.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/domain/results.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from briefing.domain.value_objects import ArticleStatus, SourceName


@dataclass
class SyncResult:
    ok: bool
    commit_sha: str | None = None
    article_count: int = 0
    error: str | None = None

    @classmethod
    def success(cls, commit_sha: str | None, article_count: int) -> "SyncResult":
        return cls(ok=True, commit_sha=commit_sha, article_count=article_count)

    @classmethod
    def failure(cls, error: str) -> "SyncResult":
        return cls(ok=False, error=error)


@dataclass
class SyncStatus:
    last_push_at: datetime | None
    last_commit_sha: str | None
    pending_count: int
    last_error: str | None


@dataclass
class AdminFilter:
    source: SourceName | None = None
    status: ArticleStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    tag: str | None = None
    query: str | None = None
    limit: int = 50
    offset: int = 0
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/domain/test_results.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/domain/results.py tests/domain/test_results.py
git commit -m "feat(domain): SyncResult, SyncStatus, AdminFilter"
```

---

### Task 1.4: 포트 정의 (Protocol)

**Files:**
- Create: `src/briefing/domain/ports.py`
- Create: `tests/domain/test_ports.py`

> 포트는 추상 인터페이스라 자체 실행 로직이 없음. 테스트는 "Protocol을 만족하는 더미 구현이 isinstance 검사를 통과한다" 정도로만 검증.

- [ ] **Step 1: 테스트 작성**

```python
# tests/domain/test_ports.py
from briefing.domain.ports import (
    ArticleRepository,
    KeywordExtractor,
    SourceAdapter,
    VaultPublisher,
    VaultSync,
)


def test_ports_are_protocols():
    # runtime_checkable Protocols 이므로 isinstance(any_object, Port) 호출 가능.
    class Dummy:
        pass

    assert isinstance(Dummy(), SourceAdapter) is False
    assert isinstance(Dummy(), KeywordExtractor) is False
    assert isinstance(Dummy(), ArticleRepository) is False
    assert isinstance(Dummy(), VaultPublisher) is False
    assert isinstance(Dummy(), VaultSync) is False
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/domain/test_ports.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/domain/ports.py
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Protocol, runtime_checkable

from briefing.domain.entities import Article
from briefing.domain.results import AdminFilter, SyncResult, SyncStatus
from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
)


@runtime_checkable
class SourceAdapter(Protocol):
    """신규 source 추가 시 이 하나만 구현."""

    name: SourceName

    def parse(self, raw_payload: dict) -> Article: ...

    def verify(self, headers: dict, raw_body: bytes) -> bool: ...


@runtime_checkable
class KeywordExtractor(Protocol):
    def extract(self, text: str) -> list[Tag]: ...


@runtime_checkable
class ArticleRepository(Protocol):
    def save(self, article: Article) -> None: ...

    def find_by_hash(self, h: PayloadHash) -> Article | None: ...

    def find_by_id(self, id: ArticleId) -> Article | None: ...

    def list_pending(self, limit: int) -> list[Article]: ...

    def list_for_admin(self, filters: AdminFilter) -> list[Article]: ...

    def update_status(
        self,
        id: ArticleId,
        status: ArticleStatus,
        *,
        output_path: Path | None = None,
        error: str | None = None,
        increment_retry: bool = False,
    ) -> None: ...

    def update_tags(self, id: ArticleId, tags: list[Tag]) -> None: ...

    def count_by_source(self) -> dict[SourceName, int]: ...

    def count_pending(self) -> int: ...


@runtime_checkable
class VaultPublisher(Protocol):
    def publish(self, article: Article) -> Path: ...


@runtime_checkable
class VaultSync(Protocol):
    def commit_and_push(self, message: str) -> SyncResult: ...

    def status(self) -> SyncStatus: ...
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/domain/test_ports.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/domain/ports.py tests/domain/test_ports.py
git commit -m "feat(domain): port protocols"
```

---

## Phase 2: Application Layer

### Task 2.1: Fake adapters (테스트 공용 유틸)

**Files:**
- Create: `tests/application/__init__.py`
- Create: `tests/application/fakes.py`

> 이 테스트는 실패할 게 없는 유틸리티 추가. 검증 테스트만 1개 둠.

- [ ] **Step 1: fake 모듈 작성**

```python
# tests/application/fakes.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from briefing.domain.entities import Article
from briefing.domain.results import AdminFilter, SyncResult, SyncStatus
from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
    payload_hash,
)


@dataclass
class FakeArticleRepository:
    by_id: dict[ArticleId, Article] = field(default_factory=dict)

    def save(self, article: Article) -> None:
        self.by_id[article.id] = article

    def find_by_hash(self, h: PayloadHash) -> Article | None:
        for a in self.by_id.values():
            if a.payload_hash == h:
                return a
        return None

    def find_by_id(self, id: ArticleId) -> Article | None:
        return self.by_id.get(id)

    def list_pending(self, limit: int) -> list[Article]:
        out = [a for a in self.by_id.values() if a.status is ArticleStatus.RECEIVED]
        return out[:limit]

    def list_for_admin(self, filters: AdminFilter) -> list[Article]:
        out = list(self.by_id.values())
        if filters.source is not None:
            out = [a for a in out if a.source == filters.source]
        if filters.status is not None:
            out = [a for a in out if a.status == filters.status]
        return out[filters.offset : filters.offset + filters.limit]

    def update_status(
        self,
        id: ArticleId,
        status: ArticleStatus,
        *,
        output_path: Path | None = None,
        error: str | None = None,
        increment_retry: bool = False,
    ) -> None:
        a = self.by_id[id]
        retry = a.retry_count + (1 if increment_retry else 0)
        self.by_id[id] = Article(
            id=a.id,
            source=a.source,
            external_id=a.external_id,
            payload_hash=a.payload_hash,
            received_at=a.received_at,
            title=a.title,
            body=a.body,
            url=a.url,
            tags=list(a.tags),
            raw_payload=dict(a.raw_payload),
            status=status,
            output_path=output_path or a.output_path,
            error=error if error is not None else a.error,
            retry_count=retry,
            processed_at=a.processed_at,
            published_at=a.published_at,
        )

    def update_tags(self, id: ArticleId, tags: list[Tag]) -> None:
        a = self.by_id[id]
        a.tags = list(tags)

    def count_by_source(self) -> dict[SourceName, int]:
        out: dict[SourceName, int] = {}
        for a in self.by_id.values():
            out[a.source] = out.get(a.source, 0) + 1
        return out

    def count_pending(self) -> int:
        return sum(1 for a in self.by_id.values() if a.status is ArticleStatus.RECEIVED)


@dataclass
class FakeExtractor:
    tags: list[Tag] = field(default_factory=lambda: [Tag("AI"), Tag("반도체")])
    raise_on_extract: bool = False

    def extract(self, text: str) -> list[Tag]:
        if self.raise_on_extract:
            raise RuntimeError("nlp failed")
        return list(self.tags)


@dataclass
class FakePublisher:
    written: list[Article] = field(default_factory=list)
    raise_on_publish: bool = False

    def publish(self, article: Article) -> Path:
        if self.raise_on_publish:
            raise RuntimeError("disk full")
        self.written.append(article)
        return Path(f"/vault/{article.source}/{article.received_at.date()}.md")


@dataclass
class FakeSync:
    pushed: int = 0
    fail_next: bool = False

    def commit_and_push(self, message: str) -> SyncResult:
        if self.fail_next:
            self.fail_next = False
            return SyncResult.failure("push rejected")
        self.pushed += 1
        return SyncResult.success(commit_sha=f"sha{self.pushed:04d}", article_count=1)

    def status(self) -> SyncStatus:
        return SyncStatus(
            last_push_at=None, last_commit_sha=None, pending_count=0, last_error=None
        )


def make_article(*, body: str = "본문", source: str = "dooray", payload: dict | None = None) -> Article:
    p = payload or {"text": body}
    return Article(
        id=ArticleId(str(uuid4())),
        source=SourceName(source),
        external_id=None,
        payload_hash=payload_hash(p),
        received_at=datetime(2026, 5, 13, 14, 32),
        title=body[:20],
        body=body,
        url=None,
        tags=[],
        raw_payload=p,
    )
```

- [ ] **Step 2: fakes 자체 sanity 테스트**

```python
# tests/application/test_fakes.py
from tests.application.fakes import FakeArticleRepository, make_article


def test_fake_repo_roundtrip():
    repo = FakeArticleRepository()
    a = make_article(body="hello")
    repo.save(a)
    assert repo.find_by_id(a.id) is a
    assert repo.find_by_hash(a.payload_hash) is a
```

- [ ] **Step 3: 통과 확인**

```powershell
pytest tests/application/test_fakes.py -v
```

Expected: 1 passed.

- [ ] **Step 4: Commit**

```powershell
git add tests/application
git commit -m "test: shared fake adapters for application tests"
```

---

### Task 2.2: IngestArticleUseCase

**Files:**
- Create: `src/briefing/application/ingest_article.py`
- Create: `tests/application/test_ingest_article.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/application/test_ingest_article.py
from briefing.application.ingest_article import IngestArticleUseCase, IngestResult
from tests.application.fakes import FakeArticleRepository, make_article


def test_ingest_new_article_stored():
    repo = FakeArticleRepository()
    uc = IngestArticleUseCase(repo)
    a = make_article(body="first")

    result = uc.execute(a)

    assert result is IngestResult.STORED
    assert repo.find_by_id(a.id) is a


def test_ingest_duplicate_payload_is_skipped():
    repo = FakeArticleRepository()
    uc = IngestArticleUseCase(repo)
    a1 = make_article(body="dup")
    a2 = make_article(body="dup")  # same payload → same hash
    assert a1.payload_hash == a2.payload_hash

    uc.execute(a1)
    result = uc.execute(a2)

    assert result is IngestResult.DUPLICATE
    assert len(repo.by_id) == 1
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/application/test_ingest_article.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/application/ingest_article.py
from __future__ import annotations

from enum import StrEnum

from briefing.domain.entities import Article
from briefing.domain.ports import ArticleRepository


class IngestResult(StrEnum):
    STORED = "stored"
    DUPLICATE = "duplicate"


class IngestArticleUseCase:
    def __init__(self, repo: ArticleRepository) -> None:
        self._repo = repo

    def execute(self, article: Article) -> IngestResult:
        if self._repo.find_by_hash(article.payload_hash) is not None:
            return IngestResult.DUPLICATE
        self._repo.save(article)
        return IngestResult.STORED
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/application/test_ingest_article.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/application/ingest_article.py tests/application/test_ingest_article.py
git commit -m "feat(application): IngestArticleUseCase with idempotency"
```

---

### Task 2.3: PublishPendingUseCase

**Files:**
- Create: `src/briefing/application/publish_pending.py`
- Create: `tests/application/test_publish_pending.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/application/test_publish_pending.py
from briefing.application.publish_pending import PublishPendingUseCase
from briefing.domain.value_objects import ArticleStatus, Tag
from tests.application.fakes import (
    FakeArticleRepository,
    FakeExtractor,
    FakePublisher,
    make_article,
)


def test_publish_pending_writes_and_marks_processed():
    repo = FakeArticleRepository()
    a = make_article(body="네이버 AI 발표")
    repo.save(a)
    uc = PublishPendingUseCase(repo, FakeExtractor(), FakePublisher(), max_retry=3)

    uc.execute(batch=10)

    out = repo.find_by_id(a.id)
    assert out.status is ArticleStatus.PROCESSED
    assert Tag("AI") in out.tags
    assert out.output_path is not None


def test_publish_pending_failure_increments_retry_and_stays_received():
    repo = FakeArticleRepository()
    a = make_article(body="x")
    repo.save(a)
    uc = PublishPendingUseCase(repo, FakeExtractor(), FakePublisher(raise_on_publish=True), max_retry=3)

    uc.execute(batch=10)

    out = repo.find_by_id(a.id)
    assert out.status is ArticleStatus.RECEIVED
    assert out.retry_count == 1
    assert out.error is not None


def test_publish_pending_exceeds_max_retry_becomes_failed():
    repo = FakeArticleRepository()
    a = make_article(body="x")
    repo.save(a)
    publisher = FakePublisher(raise_on_publish=True)
    uc = PublishPendingUseCase(repo, FakeExtractor(), publisher, max_retry=2)

    uc.execute(batch=10)
    uc.execute(batch=10)

    out = repo.find_by_id(a.id)
    assert out.status is ArticleStatus.FAILED
    assert out.retry_count == 2


def test_publish_pending_extractor_failure_still_publishes_without_tags():
    repo = FakeArticleRepository()
    a = make_article(body="x")
    repo.save(a)
    uc = PublishPendingUseCase(
        repo, FakeExtractor(raise_on_extract=True), FakePublisher(), max_retry=3
    )

    uc.execute(batch=10)

    out = repo.find_by_id(a.id)
    assert out.status is ArticleStatus.PROCESSED
    assert out.tags == []
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/application/test_publish_pending.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/application/publish_pending.py
from __future__ import annotations

import logging

from briefing.domain.ports import ArticleRepository, KeywordExtractor, VaultPublisher
from briefing.domain.value_objects import ArticleStatus

log = logging.getLogger(__name__)


class PublishPendingUseCase:
    def __init__(
        self,
        repo: ArticleRepository,
        extractor: KeywordExtractor,
        publisher: VaultPublisher,
        *,
        max_retry: int,
    ) -> None:
        self._repo = repo
        self._extractor = extractor
        self._publisher = publisher
        self._max_retry = max_retry

    def execute(self, *, batch: int) -> int:
        processed = 0
        for article in self._repo.list_pending(limit=batch):
            try:
                try:
                    tags = self._extractor.extract(article.body)
                except Exception:
                    log.warning("keyword extraction failed", exc_info=True)
                    tags = []
                self._repo.update_tags(article.id, tags)
                article.tags = list(tags)

                path = self._publisher.publish(article)
                self._repo.update_status(
                    article.id, ArticleStatus.PROCESSED, output_path=path, error=None
                )
                processed += 1
            except Exception as e:
                new_count = article.retry_count + 1
                final_status = (
                    ArticleStatus.FAILED if new_count >= self._max_retry else ArticleStatus.RECEIVED
                )
                self._repo.update_status(
                    article.id, final_status, error=repr(e), increment_retry=True
                )
                log.error("publish failed for %s", article.id, exc_info=True)
        return processed
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/application/test_publish_pending.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/application/publish_pending.py tests/application/test_publish_pending.py
git commit -m "feat(application): PublishPendingUseCase with retry"
```

---

### Task 2.4: SyncVaultUseCase

**Files:**
- Create: `src/briefing/application/sync_vault.py`
- Create: `tests/application/test_sync_vault.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/application/test_sync_vault.py
from briefing.application.sync_vault import SyncVaultUseCase
from briefing.domain.value_objects import ArticleStatus
from tests.application.fakes import FakeArticleRepository, FakeSync, make_article


def _processed(repo, body="x"):
    a = make_article(body=body)
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.PROCESSED)
    return a


def test_sync_pushes_and_marks_published():
    repo = FakeArticleRepository()
    a = _processed(repo)
    uc = SyncVaultUseCase(repo, FakeSync())

    result = uc.execute()

    assert result.ok is True
    assert repo.find_by_id(a.id).status is ArticleStatus.PUBLISHED


def test_sync_failure_leaves_status_unchanged():
    repo = FakeArticleRepository()
    a = _processed(repo)
    uc = SyncVaultUseCase(repo, FakeSync(fail_next=True))

    result = uc.execute()

    assert result.ok is False
    assert repo.find_by_id(a.id).status is ArticleStatus.PROCESSED


def test_sync_with_no_processed_articles_is_noop():
    repo = FakeArticleRepository()
    uc = SyncVaultUseCase(repo, FakeSync())

    result = uc.execute()

    assert result.ok is True
    assert result.article_count == 0
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/application/test_sync_vault.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/application/sync_vault.py
from __future__ import annotations

from datetime import datetime, timezone

from briefing.domain.ports import ArticleRepository, VaultSync
from briefing.domain.results import AdminFilter, SyncResult
from briefing.domain.value_objects import ArticleStatus


class SyncVaultUseCase:
    def __init__(self, repo: ArticleRepository, sync: VaultSync) -> None:
        self._repo = repo
        self._sync = sync

    def execute(self) -> SyncResult:
        processed = self._repo.list_for_admin(
            AdminFilter(status=ArticleStatus.PROCESSED, limit=1000)
        )
        if not processed:
            return SyncResult.success(commit_sha=None, article_count=0)

        message = f"briefing: {len(processed)} article(s) at {datetime.now(timezone.utc).isoformat()}"
        result = self._sync.commit_and_push(message)
        if not result.ok:
            return result

        for a in processed:
            self._repo.update_status(a.id, ArticleStatus.PUBLISHED)
        return SyncResult.success(commit_sha=result.commit_sha, article_count=len(processed))
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/application/test_sync_vault.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/application/sync_vault.py tests/application/test_sync_vault.py
git commit -m "feat(application): SyncVaultUseCase"
```

---

### Task 2.5: ReplayFailedUseCase + AdminQueries

**Files:**
- Create: `src/briefing/application/replay_failed.py`
- Create: `src/briefing/application/admin_queries.py`
- Create: `tests/application/test_replay_failed.py`
- Create: `tests/application/test_admin_queries.py`

- [ ] **Step 1: 테스트 작성 (replay_failed)**

```python
# tests/application/test_replay_failed.py
from briefing.application.replay_failed import ReplayFailedUseCase
from briefing.domain.value_objects import ArticleStatus
from tests.application.fakes import FakeArticleRepository, make_article


def test_replay_resets_failed_to_received():
    repo = FakeArticleRepository()
    a = make_article(body="x")
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.FAILED, error="boom")
    uc = ReplayFailedUseCase(repo)

    uc.execute()

    out = repo.find_by_id(a.id)
    assert out.status is ArticleStatus.RECEIVED
    assert out.error is None
```

- [ ] **Step 2: 테스트 작성 (admin_queries)**

```python
# tests/application/test_admin_queries.py
from briefing.application.admin_queries import AdminQueries
from briefing.domain.results import AdminFilter
from briefing.domain.value_objects import ArticleStatus
from tests.application.fakes import FakeArticleRepository, FakeSync, make_article


def test_dashboard_summary():
    repo = FakeArticleRepository()
    repo.save(make_article(body="a"))
    repo.save(make_article(body="b"))
    queries = AdminQueries(repo, FakeSync())

    summary = queries.dashboard()

    assert summary.pending_count == 2
    assert summary.per_source["dooray"] == 2


def test_list_articles_passes_filters():
    repo = FakeArticleRepository()
    repo.save(make_article(body="a"))
    queries = AdminQueries(repo, FakeSync())

    items = queries.list_articles(AdminFilter(status=ArticleStatus.RECEIVED))

    assert len(items) == 1
```

- [ ] **Step 3: 실패 확인**

```powershell
pytest tests/application/test_replay_failed.py tests/application/test_admin_queries.py -v
```

Expected: ImportError.

- [ ] **Step 4: 구현 (replay_failed)**

```python
# src/briefing/application/replay_failed.py
from __future__ import annotations

from briefing.domain.ports import ArticleRepository
from briefing.domain.results import AdminFilter
from briefing.domain.value_objects import ArticleStatus


class ReplayFailedUseCase:
    def __init__(self, repo: ArticleRepository) -> None:
        self._repo = repo

    def execute(self, *, article_id: str | None = None) -> int:
        if article_id is not None:
            self._repo.update_status(article_id, ArticleStatus.RECEIVED, error="")
            return 1
        failed = self._repo.list_for_admin(
            AdminFilter(status=ArticleStatus.FAILED, limit=1000)
        )
        for a in failed:
            self._repo.update_status(a.id, ArticleStatus.RECEIVED, error="")
        return len(failed)
```

- [ ] **Step 5: 구현 (admin_queries)**

```python
# src/briefing/application/admin_queries.py
from __future__ import annotations

from dataclasses import dataclass

from briefing.domain.entities import Article
from briefing.domain.ports import ArticleRepository, VaultSync
from briefing.domain.results import AdminFilter, SyncStatus
from briefing.domain.value_objects import SourceName


@dataclass
class DashboardSummary:
    pending_count: int
    per_source: dict[SourceName, int]
    sync: SyncStatus


class AdminQueries:
    def __init__(self, repo: ArticleRepository, sync: VaultSync) -> None:
        self._repo = repo
        self._sync = sync

    def dashboard(self) -> DashboardSummary:
        return DashboardSummary(
            pending_count=self._repo.count_pending(),
            per_source=self._repo.count_by_source(),
            sync=self._sync.status(),
        )

    def list_articles(self, filters: AdminFilter) -> list[Article]:
        return self._repo.list_for_admin(filters)

    def get_article(self, id: str) -> Article | None:
        return self._repo.find_by_id(id)
```

- [ ] **Step 6: 통과 확인**

```powershell
pytest tests/application -v
```

Expected: all green.

- [ ] **Step 7: Commit**

```powershell
git add src/briefing/application tests/application/test_replay_failed.py tests/application/test_admin_queries.py
git commit -m "feat(application): ReplayFailed + AdminQueries"
```

---

## Phase 3: Infrastructure

### Task 3.1: SQLite 스키마 + 마이그레이션

**Files:**
- Create: `src/briefing/infrastructure/persistence/schema.py`
- Create: `src/briefing/infrastructure/persistence/connection.py`
- Create: `tests/infrastructure/__init__.py`
- Create: `tests/infrastructure/persistence/__init__.py`
- Create: `tests/infrastructure/persistence/test_schema.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/infrastructure/persistence/test_schema.py
import sqlite3

from briefing.infrastructure.persistence.connection import open_connection
from briefing.infrastructure.persistence.schema import migrate


def test_migrate_creates_tables(tmp_path):
    db = tmp_path / "x.db"
    conn = open_connection(db)
    migrate(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = [r[0] for r in rows]
    assert "articles" in names
    assert "article_tags" in names
    assert "sync_log" in names
    assert "parse_failures" in names


def test_migrate_is_idempotent(tmp_path):
    db = tmp_path / "x.db"
    conn = open_connection(db)
    migrate(conn)
    migrate(conn)  # second run must not raise
    conn.execute("SELECT 1").fetchone()


def test_payload_hash_unique(tmp_path):
    db = tmp_path / "x.db"
    conn = open_connection(db)
    migrate(conn)
    conn.execute(
        "INSERT INTO articles (id, source, payload_hash, received_at, title, body, raw_payload, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("1", "dooray", "h", "2026-05-13", "t", "b", "{}", "received"),
    )
    conn.commit()
    try:
        conn.execute(
            "INSERT INTO articles (id, source, payload_hash, received_at, title, body, raw_payload, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("2", "dooray", "h", "2026-05-13", "t", "b", "{}", "received"),
        )
        conn.commit()
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/infrastructure/persistence/test_schema.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현 (connection)**

```python
# src/briefing/infrastructure/persistence/connection.py
from __future__ import annotations

import sqlite3
from pathlib import Path


def open_connection(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(db_path),
        detect_types=sqlite3.PARSE_DECLTYPES,
        isolation_level=None,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

- [ ] **Step 4: 구현 (schema)**

```python
# src/briefing/infrastructure/persistence/schema.py
from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

_SQL_V1 = """
CREATE TABLE IF NOT EXISTS articles (
  id            TEXT PRIMARY KEY,
  source        TEXT NOT NULL,
  external_id   TEXT,
  payload_hash  TEXT UNIQUE NOT NULL,
  received_at   TIMESTAMP NOT NULL,
  title         TEXT NOT NULL,
  body          TEXT NOT NULL,
  url           TEXT,
  raw_payload   TEXT NOT NULL,
  status        TEXT NOT NULL,
  output_path   TEXT,
  error         TEXT,
  retry_count   INTEGER NOT NULL DEFAULT 0,
  processed_at  TIMESTAMP,
  published_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_articles_status   ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_source   ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_received ON articles(received_at);

CREATE TABLE IF NOT EXISTS article_tags (
  article_id  TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  tag         TEXT NOT NULL,
  PRIMARY KEY (article_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_article_tags_tag ON article_tags(tag);

CREATE TABLE IF NOT EXISTS sync_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  pushed_at     TIMESTAMP NOT NULL,
  commit_sha    TEXT,
  article_count INTEGER,
  status        TEXT NOT NULL,
  error         TEXT
);

CREATE TABLE IF NOT EXISTS parse_failures (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  source       TEXT NOT NULL,
  received_at  TIMESTAMP NOT NULL,
  raw_payload  TEXT NOT NULL,
  error        TEXT NOT NULL,
  resolved     INTEGER NOT NULL DEFAULT 0
);
"""


def _current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(conn: sqlite3.Connection) -> None:
    version = _current_version(conn)
    if version < 1:
        conn.executescript(_SQL_V1)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
```

- [ ] **Step 5: 통과 확인**

```powershell
pytest tests/infrastructure/persistence/test_schema.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```powershell
git add src/briefing/infrastructure/persistence tests/infrastructure
git commit -m "feat(infra): sqlite schema + connection"
```

---

### Task 3.2: SqliteArticleRepository

**Files:**
- Create: `src/briefing/infrastructure/persistence/sqlite_article_repo.py`
- Create: `tests/infrastructure/persistence/test_sqlite_article_repo.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/infrastructure/persistence/test_sqlite_article_repo.py
from datetime import datetime, timezone
from uuid import uuid4

from briefing.domain.entities import Article
from briefing.domain.results import AdminFilter
from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
)
from briefing.infrastructure.persistence.connection import open_connection
from briefing.infrastructure.persistence.schema import migrate
from briefing.infrastructure.persistence.sqlite_article_repo import SqliteArticleRepository


def _conn(tmp_path):
    c = open_connection(tmp_path / "x.db")
    migrate(c)
    return c


def _make_article(*, body="본문", hash="a" * 64, source="dooray"):
    return Article(
        id=ArticleId(str(uuid4())),
        source=SourceName(source),
        external_id=None,
        payload_hash=PayloadHash(hash),
        received_at=datetime(2026, 5, 13, 14, 32, tzinfo=timezone.utc),
        title=body[:20],
        body=body,
        url=None,
        tags=[],
        raw_payload={"text": body},
    )


def test_save_and_find_by_id(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article()
    repo.save(a)
    out = repo.find_by_id(a.id)
    assert out.body == a.body
    assert out.status is ArticleStatus.RECEIVED


def test_find_by_hash(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="b" * 64)
    repo.save(a)
    out = repo.find_by_hash(a.payload_hash)
    assert out is not None and out.id == a.id


def test_list_pending_only_returns_received(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="c" * 64)
    b = _make_article(hash="d" * 64)
    repo.save(a)
    repo.save(b)
    repo.update_status(b.id, ArticleStatus.PROCESSED)
    pending = repo.list_pending(limit=10)
    assert [p.id for p in pending] == [a.id]


def test_update_tags_replaces_existing(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="e" * 64)
    repo.save(a)
    repo.update_tags(a.id, [Tag("AI"), Tag("반도체")])
    out = repo.find_by_id(a.id)
    assert set(out.tags) == {"AI", "반도체"}

    repo.update_tags(a.id, [Tag("뉴스")])
    out2 = repo.find_by_id(a.id)
    assert out2.tags == ["뉴스"]


def test_list_for_admin_filter_by_status(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="f" * 64)
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.FAILED, error="boom")

    items = repo.list_for_admin(AdminFilter(status=ArticleStatus.FAILED))
    assert len(items) == 1
    assert items[0].error == "boom"


def test_update_status_increments_retry(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    a = _make_article(hash="9" * 64)
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.RECEIVED, error="x", increment_retry=True)
    repo.update_status(a.id, ArticleStatus.RECEIVED, error="y", increment_retry=True)
    out = repo.find_by_id(a.id)
    assert out.retry_count == 2


def test_count_by_source_and_pending(tmp_path):
    repo = SqliteArticleRepository(_conn(tmp_path))
    repo.save(_make_article(hash="1" * 64))
    repo.save(_make_article(hash="2" * 64))
    assert repo.count_pending() == 2
    assert repo.count_by_source() == {"dooray": 2}
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/infrastructure/persistence/test_sqlite_article_repo.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/infrastructure/persistence/sqlite_article_repo.py
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from briefing.domain.entities import Article
from briefing.domain.results import AdminFilter
from briefing.domain.value_objects import (
    ArticleId,
    ArticleStatus,
    PayloadHash,
    SourceName,
    Tag,
)


class SqliteArticleRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ---------- helpers ----------

    @staticmethod
    def _row_to_article(row: sqlite3.Row, tags: list[str]) -> Article:
        return Article(
            id=ArticleId(row["id"]),
            source=SourceName(row["source"]),
            external_id=row["external_id"],
            payload_hash=PayloadHash(row["payload_hash"]),
            received_at=_to_dt(row["received_at"]),
            title=row["title"],
            body=row["body"],
            url=row["url"],
            tags=[Tag(t) for t in tags],
            raw_payload=json.loads(row["raw_payload"]),
            status=ArticleStatus(row["status"]),
            output_path=Path(row["output_path"]) if row["output_path"] else None,
            error=row["error"],
            retry_count=row["retry_count"],
            processed_at=_to_dt(row["processed_at"]) if row["processed_at"] else None,
            published_at=_to_dt(row["published_at"]) if row["published_at"] else None,
        )

    def _tags_for(self, id: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT tag FROM article_tags WHERE article_id = ? ORDER BY tag", (id,)
        ).fetchall()
        return [r["tag"] for r in rows]

    # ---------- repository methods ----------

    def save(self, article: Article) -> None:
        self._conn.execute(
            """
            INSERT INTO articles
              (id, source, external_id, payload_hash, received_at, title, body, url,
               raw_payload, status, output_path, error, retry_count,
               processed_at, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article.id,
                article.source,
                article.external_id,
                article.payload_hash,
                article.received_at,
                article.title,
                article.body,
                article.url,
                json.dumps(article.raw_payload, ensure_ascii=False),
                article.status.value,
                str(article.output_path) if article.output_path else None,
                article.error,
                article.retry_count,
                article.processed_at,
                article.published_at,
            ),
        )

    def find_by_id(self, id: ArticleId) -> Article | None:
        row = self._conn.execute("SELECT * FROM articles WHERE id = ?", (id,)).fetchone()
        if not row:
            return None
        return self._row_to_article(row, self._tags_for(row["id"]))

    def find_by_hash(self, h: PayloadHash) -> Article | None:
        row = self._conn.execute(
            "SELECT * FROM articles WHERE payload_hash = ?", (h,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_article(row, self._tags_for(row["id"]))

    def list_pending(self, limit: int) -> list[Article]:
        rows = self._conn.execute(
            "SELECT * FROM articles WHERE status = ? ORDER BY received_at LIMIT ?",
            (ArticleStatus.RECEIVED.value, limit),
        ).fetchall()
        return [self._row_to_article(r, self._tags_for(r["id"])) for r in rows]

    def list_for_admin(self, filters: AdminFilter) -> list[Article]:
        clauses = []
        params: list = []
        if filters.source is not None:
            clauses.append("source = ?")
            params.append(filters.source)
        if filters.status is not None:
            clauses.append("status = ?")
            params.append(filters.status.value)
        if filters.date_from is not None:
            clauses.append("received_at >= ?")
            params.append(filters.date_from)
        if filters.date_to is not None:
            clauses.append("received_at < ?")
            params.append(filters.date_to)
        if filters.query:
            clauses.append("(title LIKE ? OR body LIKE ?)")
            q = f"%{filters.query}%"
            params.extend([q, q])
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        sql = (
            f"SELECT * FROM articles {where} "
            f"ORDER BY received_at DESC LIMIT ? OFFSET ?"
        )
        params.extend([filters.limit, filters.offset])
        rows = self._conn.execute(sql, params).fetchall()
        out = [self._row_to_article(r, self._tags_for(r["id"])) for r in rows]
        if filters.tag:
            out = [a for a in out if filters.tag in a.tags]
        return out

    def update_status(
        self,
        id: ArticleId,
        status: ArticleStatus,
        *,
        output_path: Path | None = None,
        error: str | None = None,
        increment_retry: bool = False,
    ) -> None:
        sets = ["status = ?"]
        params: list = [status.value]
        if output_path is not None:
            sets.append("output_path = ?")
            params.append(str(output_path))
        if error is not None:
            sets.append("error = ?")
            params.append(error or None)
        if increment_retry:
            sets.append("retry_count = retry_count + 1")
        if status is ArticleStatus.PROCESSED:
            sets.append("processed_at = ?")
            params.append(datetime.now(timezone.utc))
        if status is ArticleStatus.PUBLISHED:
            sets.append("published_at = ?")
            params.append(datetime.now(timezone.utc))
        params.append(id)
        self._conn.execute(f"UPDATE articles SET {', '.join(sets)} WHERE id = ?", params)

    def update_tags(self, id: ArticleId, tags: list[Tag]) -> None:
        self._conn.execute("DELETE FROM article_tags WHERE article_id = ?", (id,))
        self._conn.executemany(
            "INSERT INTO article_tags (article_id, tag) VALUES (?, ?)",
            [(id, t) for t in tags],
        )

    def count_by_source(self) -> dict[SourceName, int]:
        rows = self._conn.execute(
            "SELECT source, COUNT(*) AS c FROM articles GROUP BY source"
        ).fetchall()
        return {SourceName(r["source"]): r["c"] for r in rows}

    def count_pending(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM articles WHERE status = ?",
            (ArticleStatus.RECEIVED.value,),
        ).fetchone()
        return int(row["c"])


def _to_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/infrastructure/persistence/test_sqlite_article_repo.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/infrastructure/persistence/sqlite_article_repo.py tests/infrastructure/persistence/test_sqlite_article_repo.py
git commit -m "feat(infra): SqliteArticleRepository"
```

---

### Task 3.3: KiwiKeywordExtractor + 불용어 사전

**Files:**
- Create: `src/briefing/infrastructure/nlp/kiwi_extractor.py`
- Create: `data/stopwords.txt`
- Create: `tests/infrastructure/nlp/__init__.py`
- Create: `tests/infrastructure/nlp/test_kiwi_extractor.py`

- [ ] **Step 1: 불용어 사전 작성**

```
# data/stopwords.txt — 한 줄에 하나
것
수
때
등
및
또는
그리고
하지만
때문
경우
```

- [ ] **Step 2: 테스트 작성**

```python
# tests/infrastructure/nlp/test_kiwi_extractor.py
from pathlib import Path

from briefing.infrastructure.nlp.kiwi_extractor import KiwiKeywordExtractor


STOPWORDS = Path("data/stopwords.txt")


def test_extract_korean_nouns():
    ex = KiwiKeywordExtractor(stopwords_path=STOPWORDS, top_n=5)
    tags = ex.extract("네이버가 새로운 AI 반도체를 발표했다. 인공지능 시장 경쟁이 치열하다.")
    assert "네이버" in tags
    assert "반도체" in tags
    # 불용어/짧은 토큰은 제외되어야 함
    assert "것" not in tags


def test_extract_empty_text_returns_empty():
    ex = KiwiKeywordExtractor(stopwords_path=STOPWORDS, top_n=5)
    assert ex.extract("") == []


def test_extract_respects_top_n():
    ex = KiwiKeywordExtractor(stopwords_path=STOPWORDS, top_n=2)
    tags = ex.extract("네이버 카카오 삼성 LG SK 현대 두산")
    assert len(tags) <= 2
```

- [ ] **Step 3: 실패 확인**

```powershell
pytest tests/infrastructure/nlp/test_kiwi_extractor.py -v
```

Expected: ImportError.

- [ ] **Step 4: 구현**

```python
# src/briefing/infrastructure/nlp/kiwi_extractor.py
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
```

- [ ] **Step 5: 통과 확인**

```powershell
pytest tests/infrastructure/nlp/test_kiwi_extractor.py -v
```

Expected: 3 passed (Kiwi 초기 로드로 첫 실행은 다소 느림).

- [ ] **Step 6: Commit**

```powershell
git add src/briefing/infrastructure/nlp data/stopwords.txt tests/infrastructure/nlp
git commit -m "feat(infra): KiwiKeywordExtractor + stopwords"
```

---

### Task 3.4: MarkdownVaultPublisher

**Files:**
- Create: `src/briefing/infrastructure/vault/markdown_publisher.py`
- Create: `tests/infrastructure/vault/__init__.py`
- Create: `tests/infrastructure/vault/test_markdown_publisher.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/infrastructure/vault/test_markdown_publisher.py
from datetime import datetime, timezone
from pathlib import Path

from briefing.domain.entities import Article
from briefing.domain.value_objects import ArticleId, PayloadHash, SourceName, Tag
from briefing.infrastructure.vault.markdown_publisher import MarkdownVaultPublisher


def _article(**overrides):
    base = dict(
        id=ArticleId("11111111-1111-1111-1111-111111111111"),
        source=SourceName("dooray"),
        external_id=None,
        payload_hash=PayloadHash("a" * 64),
        received_at=datetime(2026, 5, 13, 14, 32, tzinfo=timezone.utc),
        title="네이버 AI",
        body="네이버가 새 모델을 발표했다.",
        url="https://example.com/a",
        tags=[Tag("네이버"), Tag("AI")],
        raw_payload={},
    )
    base.update(overrides)
    return Article(**base)


def test_publish_creates_dated_file(tmp_path):
    pub = MarkdownVaultPublisher(tmp_path)
    path = pub.publish(_article())
    assert path == tmp_path / "dooray" / "2026-05-13.md"
    content = path.read_text(encoding="utf-8")
    assert "네이버 AI" in content
    assert "#네이버" in content
    assert "https://example.com/a" in content


def test_publish_appends_to_existing(tmp_path):
    pub = MarkdownVaultPublisher(tmp_path)
    pub.publish(_article(payload_hash=PayloadHash("a" * 64), body="첫 번째"))
    pub.publish(
        _article(
            id=ArticleId("22222222-2222-2222-2222-222222222222"),
            payload_hash=PayloadHash("b" * 64),
            body="두 번째",
        )
    )
    path = tmp_path / "dooray" / "2026-05-13.md"
    content = path.read_text(encoding="utf-8")
    assert "첫 번째" in content
    assert "두 번째" in content
    # 헤더는 한 번만
    assert content.count("# 2026-05-13") == 1


def test_publish_handles_missing_url_and_empty_tags(tmp_path):
    pub = MarkdownVaultPublisher(tmp_path)
    path = pub.publish(_article(url=None, tags=[]))
    content = path.read_text(encoding="utf-8")
    assert "**url**" not in content
    assert "**tags**: (none)" in content
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/infrastructure/vault/test_markdown_publisher.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/infrastructure/vault/markdown_publisher.py
from __future__ import annotations

from pathlib import Path

from briefing.domain.entities import Article


class MarkdownVaultPublisher:
    """vault/<source>/<YYYY-MM-DD>.md 파일에 append 방식으로 기록."""

    def __init__(self, vault_root: Path) -> None:
        self._vault_root = Path(vault_root)

    def publish(self, article: Article) -> Path:
        local_dt = article.received_at  # UTC 그대로 사용 (간단)
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
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/infrastructure/vault/test_markdown_publisher.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/infrastructure/vault tests/infrastructure/vault
git commit -m "feat(infra): MarkdownVaultPublisher"
```

---

### Task 3.5: GitVaultSync

**Files:**
- Create: `src/briefing/infrastructure/sync/git_sync.py`
- Create: `tests/infrastructure/sync/__init__.py`
- Create: `tests/infrastructure/sync/test_git_sync.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/infrastructure/sync/test_git_sync.py
from pathlib import Path

from git import Repo

from briefing.infrastructure.sync.git_sync import GitVaultSync


def _setup_repos(tmp_path):
    remote = tmp_path / "remote.git"
    Repo.init(remote, bare=True)
    work = tmp_path / "work"
    repo = Repo.init(work)
    repo.git.checkout("-b", "main")
    repo.git.commit("--allow-empty", "-m", "init")
    repo.create_remote("origin", str(remote))
    repo.git.push("--set-upstream", "origin", "main")
    return work, remote


def test_no_changes_returns_success_with_zero(tmp_path):
    work, _ = _setup_repos(tmp_path)
    sync = GitVaultSync(work, remote="origin", branch="main")
    result = sync.commit_and_push("nothing")
    assert result.ok is True
    assert result.article_count == 0


def test_commit_and_push_with_new_file(tmp_path):
    work, remote = _setup_repos(tmp_path)
    (work / "dooray").mkdir()
    (work / "dooray" / "2026-05-13.md").write_text("hello", encoding="utf-8")

    sync = GitVaultSync(work, remote="origin", branch="main")
    result = sync.commit_and_push("first")

    assert result.ok is True
    assert result.commit_sha is not None

    # remote에 push되었는지 확인
    remote_repo = Repo(remote)
    refs = [r.name for r in remote_repo.refs]
    assert "main" in refs


def test_status_reports_last_commit(tmp_path):
    work, _ = _setup_repos(tmp_path)
    (work / "x.md").write_text("y", encoding="utf-8")
    sync = GitVaultSync(work, remote="origin", branch="main")
    sync.commit_and_push("c1")
    status = sync.status()
    assert status.last_commit_sha is not None
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/infrastructure/sync/test_git_sync.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/infrastructure/sync/git_sync.py
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from git import Repo
from git.exc import GitCommandError

from briefing.domain.results import SyncResult, SyncStatus


class GitVaultSync:
    def __init__(self, vault_path: Path, *, remote: str = "origin", branch: str = "main") -> None:
        self._vault = Path(vault_path)
        self._remote = remote
        self._branch = branch
        self._last_push_at: datetime | None = None
        self._last_error: str | None = None

    def _repo(self) -> Repo:
        return Repo(self._vault)

    def commit_and_push(self, message: str) -> SyncResult:
        try:
            repo = self._repo()
        except Exception as e:
            return SyncResult.failure(f"open failed: {e}")

        try:
            repo.git.add("--all")
            if not repo.is_dirty(untracked_files=True) and not repo.index.diff("HEAD"):
                return SyncResult.success(commit_sha=None, article_count=0)

            repo.index.commit(message)
            sha = repo.head.commit.hexsha
            repo.git.push(self._remote, self._branch)
            self._last_push_at = datetime.now(timezone.utc)
            self._last_error = None
            return SyncResult.success(commit_sha=sha, article_count=1)
        except GitCommandError as e:
            self._last_error = str(e)
            return SyncResult.failure(str(e))
        except Exception as e:
            self._last_error = repr(e)
            return SyncResult.failure(repr(e))

    def status(self) -> SyncStatus:
        try:
            repo = self._repo()
            sha = repo.head.commit.hexsha
        except Exception:
            sha = None
        return SyncStatus(
            last_push_at=self._last_push_at,
            last_commit_sha=sha,
            pending_count=0,
            last_error=self._last_error,
        )
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/infrastructure/sync/test_git_sync.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/infrastructure/sync tests/infrastructure/sync
git commit -m "feat(infra): GitVaultSync"
```

---

### Task 3.6: DoorayAdapter + SourceRegistry

**Files:**
- Create: `src/briefing/infrastructure/sources/dooray.py`
- Create: `src/briefing/infrastructure/sources/registry.py`
- Create: `tests/infrastructure/sources/__init__.py`
- Create: `tests/infrastructure/sources/test_dooray.py`
- Create: `tests/infrastructure/sources/test_registry.py`

- [ ] **Step 1: 테스트 작성 (DoorayAdapter)**

```python
# tests/infrastructure/sources/test_dooray.py
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
```

- [ ] **Step 2: 테스트 작성 (SourceRegistry)**

```python
# tests/infrastructure/sources/test_registry.py
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
```

- [ ] **Step 3: 실패 확인**

```powershell
pytest tests/infrastructure/sources -v
```

Expected: ImportError.

- [ ] **Step 4: 구현 (DoorayAdapter)**

```python
# src/briefing/infrastructure/sources/dooray.py
from __future__ import annotations

import hmac
from datetime import datetime, timezone
from uuid import uuid4

from briefing.domain.entities import Article
from briefing.domain.value_objects import (
    ArticleId,
    PayloadHash,
    SourceName,
    payload_hash,
)


class DoorayAdapter:
    name = SourceName("dooray")

    def __init__(self, *, token: str | None) -> None:
        self._token = token

    def verify(self, headers: dict, raw_body: bytes) -> bool:
        if not self._token:
            return True
        provided = headers.get("X-Dooray-Token") or headers.get("x-dooray-token")
        if not provided:
            return False
        return hmac.compare_digest(provided, self._token)

    def parse(self, raw_payload: dict) -> Article:
        text = raw_payload.get("text", "") or ""
        attachments = raw_payload.get("attachments") or []

        title = ""
        url: str | None = None
        body_parts: list[str] = []

        if text:
            body_parts.append(text)
        if attachments:
            att = attachments[0]
            title = att.get("title") or ""
            url = att.get("titleLink")
            for a in attachments:
                t = a.get("text")
                if t:
                    body_parts.append(t)

        body = "\n\n".join(p for p in body_parts if p).strip()
        if not title:
            title = body[:40] if body else "(no title)"

        return Article(
            id=ArticleId(str(uuid4())),
            source=self.name,
            external_id=raw_payload.get("event_id") or raw_payload.get("messageId"),
            payload_hash=PayloadHash(payload_hash(raw_payload)),
            received_at=datetime.now(timezone.utc),
            title=title,
            body=body,
            url=url,
            tags=[],
            raw_payload=raw_payload,
        )
```

- [ ] **Step 5: 구현 (SourceRegistry)**

```python
# src/briefing/infrastructure/sources/registry.py
from __future__ import annotations

from briefing.domain.ports import SourceAdapter
from briefing.domain.value_objects import SourceName


class SourceRegistry:
    def __init__(self) -> None:
        self._by_name: dict[SourceName, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        if adapter.name in self._by_name:
            raise ValueError(f"source already registered: {adapter.name}")
        self._by_name[adapter.name] = adapter

    def get(self, name: SourceName) -> SourceAdapter | None:
        return self._by_name.get(name)

    def list_all(self) -> list[SourceAdapter]:
        return list(self._by_name.values())
```

- [ ] **Step 6: 통과 확인**

```powershell
pytest tests/infrastructure/sources -v
```

Expected: 7 passed.

- [ ] **Step 7: Commit**

```powershell
git add src/briefing/infrastructure/sources tests/infrastructure/sources
git commit -m "feat(infra): DoorayAdapter + SourceRegistry"
```

---

## Phase 4: Interface (FastAPI + Admin UI)

### Task 4.1: Settings

**Files:**
- Create: `src/briefing/interface/settings.py`
- Create: `.env.example`
- Create: `tests/interface/__init__.py`
- Create: `tests/interface/test_settings.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/interface/test_settings.py
import os

from briefing.interface.settings import Settings


def test_settings_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("BRIEFING_DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.setenv("BRIEFING_VAULT_PATH", str(tmp_path / "vault"))
    monkeypatch.setenv("BRIEFING_ADMIN_USER", "u")
    monkeypatch.setenv("BRIEFING_ADMIN_PASSWORD", "p")
    s = Settings()
    assert s.db_path == tmp_path / "db.sqlite"
    assert s.vault_path == tmp_path / "vault"
    assert s.admin_user == "u"
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/interface/test_settings.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현 (Settings)**

```python
# src/briefing/interface/settings.py
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BRIEFING_", env_file=".env", extra="ignore")

    # paths
    db_path: Path = Field(default=Path("data/briefing.db"))
    vault_path: Path = Field(default=Path("vault"))
    log_path: Path = Field(default=Path("data/briefing.log"))
    stopwords_path: Path = Field(default=Path("data/stopwords.txt"))

    # git
    git_remote: str = "origin"
    git_branch: str = "main"
    git_user_name: str = "briefing-bot"
    git_user_email: str = "briefing@example.com"

    # worker
    worker_interval_sec: int = 5
    sync_idle_sec: int = 60
    max_retry: int = 3

    # source secrets
    dooray_token: str | None = None

    # admin
    admin_user: str = "admin"
    admin_password: str = "change-me"

    # nlp
    keyword_top_n: int = 5
```

- [ ] **Step 4: `.env.example` 작성**

```
BRIEFING_DB_PATH=data/briefing.db
BRIEFING_VAULT_PATH=vault
BRIEFING_LOG_PATH=data/briefing.log
BRIEFING_STOPWORDS_PATH=data/stopwords.txt

BRIEFING_GIT_REMOTE=origin
BRIEFING_GIT_BRANCH=main
BRIEFING_GIT_USER_NAME=briefing-bot
BRIEFING_GIT_USER_EMAIL=briefing@example.com

BRIEFING_WORKER_INTERVAL_SEC=5
BRIEFING_SYNC_IDLE_SEC=60
BRIEFING_MAX_RETRY=3

BRIEFING_DOORAY_TOKEN=

BRIEFING_ADMIN_USER=admin
BRIEFING_ADMIN_PASSWORD=change-me

BRIEFING_KEYWORD_TOP_N=5
```

- [ ] **Step 5: 통과 확인**

```powershell
pytest tests/interface/test_settings.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Commit**

```powershell
git add src/briefing/interface/settings.py .env.example tests/interface/test_settings.py
git commit -m "feat(interface): Settings + .env.example"
```

---

### Task 4.2: Webhook 라우터

**Files:**
- Create: `src/briefing/interface/webhook/routes.py`
- Create: `tests/interface/test_webhook_routes.py`

> 이 task는 composition root(`app.py`)가 아직 없으므로, 테스트에서 미니멀 app을 직접 구성해서 검증.

- [ ] **Step 1: 테스트 작성**

```python
# tests/interface/test_webhook_routes.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from briefing.application.ingest_article import IngestArticleUseCase
from briefing.infrastructure.sources.dooray import DoorayAdapter
from briefing.infrastructure.sources.registry import SourceRegistry
from briefing.interface.webhook.routes import build_webhook_router
from tests.application.fakes import FakeArticleRepository


def _make_app(*, token: str | None = None) -> tuple[FastAPI, FakeArticleRepository]:
    repo = FakeArticleRepository()
    ingest = IngestArticleUseCase(repo)
    sources = SourceRegistry()
    sources.register(DoorayAdapter(token=token))
    app = FastAPI()
    app.include_router(build_webhook_router(sources, ingest))
    return app, repo


def test_webhook_stores_new_article():
    app, repo = _make_app()
    client = TestClient(app)
    r = client.post("/webhook/dooray", json={"text": "테스트 메시지"})
    assert r.status_code == 200
    assert r.json()["status"] == "stored"
    assert len(repo.by_id) == 1


def test_webhook_idempotent():
    app, repo = _make_app()
    client = TestClient(app)
    body = {"text": "동일 메시지"}
    client.post("/webhook/dooray", json=body)
    r = client.post("/webhook/dooray", json=body)
    assert r.status_code == 200
    assert r.json()["status"] == "duplicate"
    assert len(repo.by_id) == 1


def test_webhook_unknown_source_returns_404():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.post("/webhook/unknown", json={"text": "x"})
    assert r.status_code == 404


def test_webhook_rejects_invalid_token():
    app, _ = _make_app(token="s3cret")
    client = TestClient(app)
    r = client.post("/webhook/dooray", headers={"X-Dooray-Token": "wrong"}, json={"text": "x"})
    assert r.status_code == 401


def test_webhook_empty_body_returns_400():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.post("/webhook/dooray", json={})
    assert r.status_code == 400
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/interface/test_webhook_routes.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/interface/webhook/routes.py
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from briefing.application.ingest_article import IngestArticleUseCase, IngestResult
from briefing.domain.value_objects import SourceName
from briefing.infrastructure.sources.registry import SourceRegistry

log = logging.getLogger(__name__)


def build_webhook_router(
    sources: SourceRegistry, ingest: IngestArticleUseCase
) -> APIRouter:
    router = APIRouter()

    @router.post("/webhook/{source}")
    async def webhook(source: str, request: Request):
        adapter = sources.get(SourceName(source))
        if adapter is None:
            raise HTTPException(status_code=404, detail=f"unknown source: {source}")

        raw_body = await request.body()
        headers = {k: v for k, v in request.headers.items()}

        if not adapter.verify(headers, raw_body):
            raise HTTPException(status_code=401, detail="signature verification failed")

        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="invalid json")

        if not payload:
            raise HTTPException(status_code=400, detail="empty payload")

        try:
            article = adapter.parse(payload)
        except Exception as e:
            log.exception("parse failed for source=%s", source)
            return {"status": "parse_failed", "error": repr(e)}

        result = ingest.execute(article)
        return {"status": result.value, "id": article.id}

    return router
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/interface/test_webhook_routes.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/interface/webhook tests/interface/test_webhook_routes.py
git commit -m "feat(interface): webhook router with idempotency/verify"
```

---

### Task 4.3: Admin 인증 + 베이스 템플릿

**Files:**
- Create: `src/briefing/interface/admin/auth.py`
- Create: `src/briefing/interface/admin/templates/base.html`
- Create: `tests/interface/test_admin_auth.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/interface/test_admin_auth.py
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from briefing.interface.admin.auth import build_admin_auth_dependency


def _app():
    require = build_admin_auth_dependency("u", "p")
    app = FastAPI()

    @app.get("/admin/ping")
    def ping(_=Depends(require)):
        return {"ok": True}

    return app


def test_unauthenticated_returns_401():
    c = TestClient(_app())
    assert c.get("/admin/ping").status_code == 401


def test_wrong_credentials_returns_401():
    c = TestClient(_app())
    assert c.get("/admin/ping", auth=("u", "wrong")).status_code == 401


def test_correct_credentials_passes():
    c = TestClient(_app())
    r = c.get("/admin/ping", auth=("u", "p"))
    assert r.status_code == 200 and r.json() == {"ok": True}
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/interface/test_admin_auth.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현 (auth)**

```python
# src/briefing/interface/admin/auth.py
from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials


def build_admin_auth_dependency(user: str, password: str):
    basic = HTTPBasic()

    def require_admin(creds: HTTPBasicCredentials = Depends(basic)) -> str:
        ok_user = secrets.compare_digest(creds.username, user)
        ok_pw = secrets.compare_digest(creds.password, password)
        if not (ok_user and ok_pw):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid credentials",
                headers={"WWW-Authenticate": 'Basic realm="briefing"'},
            )
        return creds.username

    return require_admin
```

- [ ] **Step 4: 기본 템플릿 작성**

```html
<!-- src/briefing/interface/admin/templates/base.html -->
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{% block title %}Briefing Admin{% endblock %}</title>
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 1100px; margin: 24px auto; padding: 0 16px; color: #222; }
    nav a { margin-right: 12px; text-decoration: none; color: #06c; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 6px 8px; border-bottom: 1px solid #eee; text-align: left; vertical-align: top; }
    .badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 12px; background: #eef; }
    .ok { color: #080; } .err { color: #b00; }
    pre { background: #f6f8fa; padding: 8px; overflow: auto; }
  </style>
</head>
<body>
  <nav>
    <strong>Briefing</strong>
    <a href="/admin">Dashboard</a>
    <a href="/admin/articles">Articles</a>
    <a href="/admin/sync">Sync</a>
    <a href="/admin/sources">Sources</a>
    <a href="/admin/logs">Logs</a>
  </nav>
  <hr>
  {% block body %}{% endblock %}
</body>
</html>
```

- [ ] **Step 5: 통과 확인**

```powershell
pytest tests/interface/test_admin_auth.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```powershell
git add src/briefing/interface/admin tests/interface/test_admin_auth.py
git commit -m "feat(interface): admin basic auth + base template"
```

---

### Task 4.4: Admin 라우터 (대시보드/목록/상세/싱크/소스/로그/리플레이)

**Files:**
- Create: `src/briefing/interface/admin/routes.py`
- Create: `src/briefing/interface/admin/templates/dashboard.html`
- Create: `src/briefing/interface/admin/templates/articles_list.html`
- Create: `src/briefing/interface/admin/templates/article_detail.html`
- Create: `src/briefing/interface/admin/templates/sync.html`
- Create: `src/briefing/interface/admin/templates/sources.html`
- Create: `src/briefing/interface/admin/templates/logs.html`
- Create: `tests/interface/test_admin_routes.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/interface/test_admin_routes.py
from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from briefing.application.admin_queries import AdminQueries
from briefing.application.replay_failed import ReplayFailedUseCase
from briefing.application.sync_vault import SyncVaultUseCase
from briefing.domain.value_objects import ArticleStatus
from briefing.infrastructure.sources.dooray import DoorayAdapter
from briefing.infrastructure.sources.registry import SourceRegistry
from briefing.interface.admin.routes import build_admin_router
from tests.application.fakes import (
    FakeArticleRepository,
    FakeSync,
    make_article,
)

TEMPLATES_DIR = Path("src/briefing/interface/admin/templates")


def _make_app() -> tuple[FastAPI, FakeArticleRepository, FakeSync]:
    repo = FakeArticleRepository()
    sync = FakeSync()
    sources = SourceRegistry()
    sources.register(DoorayAdapter(token=None))
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app = FastAPI()
    app.include_router(
        build_admin_router(
            templates=templates,
            queries=AdminQueries(repo, sync),
            sync_use_case=SyncVaultUseCase(repo, sync),
            replay_use_case=ReplayFailedUseCase(repo),
            sources=sources,
            log_path=Path("nonexistent.log"),
            require_admin=lambda: "admin",
        )
    )
    return app, repo, sync


def test_dashboard_renders_with_zero_articles():
    app, _, _ = _make_app()
    r = TestClient(app).get("/admin")
    assert r.status_code == 200
    assert "Dashboard" in r.text


def test_articles_list_renders():
    app, repo, _ = _make_app()
    repo.save(make_article(body="x"))
    r = TestClient(app).get("/admin/articles")
    assert r.status_code == 200
    assert "x" in r.text


def test_article_detail_404_when_missing():
    app, _, _ = _make_app()
    r = TestClient(app).get("/admin/articles/missing")
    assert r.status_code == 404


def test_article_retry_resets_failed():
    app, repo, _ = _make_app()
    a = make_article(body="x")
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.FAILED, error="boom")
    r = TestClient(app).post(f"/admin/articles/{a.id}/retry")
    assert r.status_code == 200
    assert repo.find_by_id(a.id).status is ArticleStatus.RECEIVED


def test_sync_manual_push_triggers_use_case():
    app, repo, sync = _make_app()
    a = make_article(body="x")
    repo.save(a)
    repo.update_status(a.id, ArticleStatus.PROCESSED)
    r = TestClient(app).post("/admin/sync/push")
    assert r.status_code == 200
    assert sync.pushed == 1


def test_sources_page_lists_dooray():
    app, _, _ = _make_app()
    r = TestClient(app).get("/admin/sources")
    assert "dooray" in r.text


def test_logs_page_handles_missing_log_file():
    app, _, _ = _make_app()
    r = TestClient(app).get("/admin/logs")
    assert r.status_code == 200
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/interface/test_admin_routes.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현 (routes)**

```python
# src/briefing/interface/admin/routes.py
from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from briefing.application.admin_queries import AdminQueries
from briefing.application.replay_failed import ReplayFailedUseCase
from briefing.application.sync_vault import SyncVaultUseCase
from briefing.domain.results import AdminFilter
from briefing.domain.value_objects import ArticleStatus, SourceName
from briefing.infrastructure.sources.registry import SourceRegistry


def build_admin_router(
    *,
    templates: Jinja2Templates,
    queries: AdminQueries,
    sync_use_case: SyncVaultUseCase,
    replay_use_case: ReplayFailedUseCase,
    sources: SourceRegistry,
    log_path: Path,
    require_admin: Callable[[], str],
) -> APIRouter:
    router = APIRouter()
    auth_dep = Depends(require_admin)

    @router.get("/admin", response_class=HTMLResponse, dependencies=[auth_dep])
    def dashboard(request: Request):
        summary = queries.dashboard()
        return templates.TemplateResponse(
            "dashboard.html", {"request": request, "summary": summary}
        )

    @router.get("/admin/articles", response_class=HTMLResponse, dependencies=[auth_dep])
    def articles_list(
        request: Request,
        source: str | None = None,
        status: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ):
        f = AdminFilter(
            source=SourceName(source) if source else None,
            status=ArticleStatus(status) if status else None,
            query=q,
            limit=limit,
            offset=offset,
        )
        items = queries.list_articles(f)
        return templates.TemplateResponse(
            "articles_list.html",
            {"request": request, "items": items, "filter": f},
        )

    @router.get("/admin/articles/{id}", response_class=HTMLResponse, dependencies=[auth_dep])
    def article_detail(request: Request, id: str):
        a = queries.get_article(id)
        if a is None:
            raise HTTPException(404)
        return templates.TemplateResponse(
            "article_detail.html", {"request": request, "a": a}
        )

    @router.post("/admin/articles/{id}/retry", dependencies=[auth_dep])
    def article_retry(id: str):
        replay_use_case.execute(article_id=id)
        return RedirectResponse(url=f"/admin/articles/{id}", status_code=303)

    @router.get("/admin/sync", response_class=HTMLResponse, dependencies=[auth_dep])
    def sync_page(request: Request):
        summary = queries.dashboard()
        return templates.TemplateResponse(
            "sync.html", {"request": request, "summary": summary}
        )

    @router.post("/admin/sync/push", dependencies=[auth_dep])
    def sync_push():
        result = sync_use_case.execute()
        return {"ok": result.ok, "commit_sha": result.commit_sha, "error": result.error}

    @router.get("/admin/sources", response_class=HTMLResponse, dependencies=[auth_dep])
    def sources_page(request: Request):
        per_source = queries.dashboard().per_source
        items = [
            {"name": a.name, "count": per_source.get(a.name, 0)}
            for a in sources.list_all()
        ]
        return templates.TemplateResponse(
            "sources.html", {"request": request, "items": items}
        )

    @router.get("/admin/logs", response_class=HTMLResponse, dependencies=[auth_dep])
    def logs_page(request: Request, tail: int = 200):
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            lines = lines[-tail:]
        else:
            lines = []
        return templates.TemplateResponse(
            "logs.html", {"request": request, "lines": lines, "tail": tail}
        )

    @router.post("/admin/replay", dependencies=[auth_dep])
    def replay_all():
        count = replay_use_case.execute()
        return {"replayed": count}

    return router
```

- [ ] **Step 4: 템플릿 작성**

`dashboard.html`:
```html
{% extends "base.html" %}
{% block title %}Dashboard — Briefing{% endblock %}
{% block body %}
<h1>Dashboard</h1>
<ul>
  <li>Pending: <strong>{{ summary.pending_count }}</strong></li>
  <li>Per source:
    <ul>{% for k, v in summary.per_source.items() %}<li>{{ k }}: {{ v }}</li>{% endfor %}</ul>
  </li>
  <li>Last push: {{ summary.sync.last_push_at or "—" }} ({{ summary.sync.last_commit_sha or "—" }})</li>
  <li>Last sync error: {{ summary.sync.last_error or "—" }}</li>
</ul>
{% endblock %}
```

`articles_list.html`:
```html
{% extends "base.html" %}
{% block body %}
<h1>Articles</h1>
<form method="get" action="/admin/articles">
  <input type="text" name="q" value="{{ filter.query or '' }}" placeholder="search">
  <select name="status">
    <option value="">(any)</option>
    {% for s in ["received", "processed", "published", "failed"] %}
    <option value="{{ s }}" {% if filter.status and filter.status.value == s %}selected{% endif %}>{{ s }}</option>
    {% endfor %}
  </select>
  <button type="submit">Filter</button>
</form>
<table>
  <thead><tr><th>time</th><th>source</th><th>title</th><th>status</th><th>tags</th></tr></thead>
  <tbody>
  {% for a in items %}
    <tr>
      <td>{{ a.received_at }}</td>
      <td>{{ a.source }}</td>
      <td><a href="/admin/articles/{{ a.id }}">{{ a.title }}</a></td>
      <td><span class="badge">{{ a.status.value }}</span></td>
      <td>{% for t in a.tags %}#{{ t }} {% endfor %}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

`article_detail.html`:
```html
{% extends "base.html" %}
{% block body %}
<h1>{{ a.title }}</h1>
<p><strong>source:</strong> {{ a.source }} · <strong>status:</strong> {{ a.status.value }} ·
   <strong>received:</strong> {{ a.received_at }}</p>
{% if a.url %}<p><strong>url:</strong> <a href="{{ a.url }}">{{ a.url }}</a></p>{% endif %}
<p><strong>tags:</strong> {% for t in a.tags %}#{{ t }} {% endfor %}</p>
{% if a.error %}<p class="err"><strong>error:</strong> {{ a.error }}</p>{% endif %}
<h3>Body</h3>
<pre>{{ a.body }}</pre>
<h3>Raw payload</h3>
<pre>{{ a.raw_payload }}</pre>
<form method="post" action="/admin/articles/{{ a.id }}/retry">
  <button type="submit">Retry</button>
</form>
{% endblock %}
```

`sync.html`:
```html
{% extends "base.html" %}
{% block body %}
<h1>Sync</h1>
<p>Last push: {{ summary.sync.last_push_at or "—" }}</p>
<p>Last commit: {{ summary.sync.last_commit_sha or "—" }}</p>
<p>Last error: <span class="err">{{ summary.sync.last_error or "—" }}</span></p>
<button hx-post="/admin/sync/push" hx-swap="none">Manual push</button>
{% endblock %}
```

`sources.html`:
```html
{% extends "base.html" %}
{% block body %}
<h1>Sources</h1>
<table>
  <thead><tr><th>name</th><th>count</th></tr></thead>
  <tbody>
  {% for s in items %}<tr><td>{{ s.name }}</td><td>{{ s.count }}</td></tr>{% endfor %}
  </tbody>
</table>
{% endblock %}
```

`logs.html`:
```html
{% extends "base.html" %}
{% block body %}
<h1>Logs (tail {{ tail }})</h1>
{% if lines %}<pre>{% for ln in lines %}{{ ln }}
{% endfor %}</pre>{% else %}<p>(log file not found)</p>{% endif %}
{% endblock %}
```

- [ ] **Step 5: 통과 확인**

```powershell
pytest tests/interface/test_admin_routes.py -v
```

Expected: 7 passed.

- [ ] **Step 6: Commit**

```powershell
git add src/briefing/interface/admin tests/interface/test_admin_routes.py
git commit -m "feat(interface): admin routes + templates"
```

---

## Phase 5: Background Worker + Composition Root

### Task 5.1: Background worker

**Files:**
- Create: `src/briefing/worker/background.py`
- Create: `tests/worker/__init__.py`
- Create: `tests/worker/test_background.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/worker/test_background.py
import asyncio

import pytest

from briefing.application.publish_pending import PublishPendingUseCase
from briefing.application.sync_vault import SyncVaultUseCase
from briefing.domain.value_objects import ArticleStatus
from briefing.worker.background import BackgroundWorker
from tests.application.fakes import (
    FakeArticleRepository,
    FakeExtractor,
    FakePublisher,
    FakeSync,
    make_article,
)


@pytest.mark.asyncio
async def test_worker_processes_pending():
    repo = FakeArticleRepository()
    repo.save(make_article(body="x"))
    publish = PublishPendingUseCase(repo, FakeExtractor(), FakePublisher(), max_retry=3)
    sync = SyncVaultUseCase(repo, FakeSync())
    w = BackgroundWorker(publish, sync, interval_sec=0.01, sync_idle_sec=0.01)

    task = asyncio.create_task(w.run())
    await asyncio.sleep(0.1)
    w.stop()
    await task

    assert all(a.status is ArticleStatus.PUBLISHED for a in repo.by_id.values())


@pytest.mark.asyncio
async def test_worker_stops_cleanly_on_empty_queue():
    repo = FakeArticleRepository()
    publish = PublishPendingUseCase(repo, FakeExtractor(), FakePublisher(), max_retry=3)
    sync = SyncVaultUseCase(repo, FakeSync())
    w = BackgroundWorker(publish, sync, interval_sec=0.01, sync_idle_sec=0.01)

    task = asyncio.create_task(w.run())
    await asyncio.sleep(0.05)
    w.stop()
    await task
    # 이 시점에 예외 없이 종료되면 통과
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/worker/test_background.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/worker/background.py
from __future__ import annotations

import asyncio
import logging
import time

from briefing.application.publish_pending import PublishPendingUseCase
from briefing.application.sync_vault import SyncVaultUseCase

log = logging.getLogger(__name__)


class BackgroundWorker:
    def __init__(
        self,
        publish: PublishPendingUseCase,
        sync: SyncVaultUseCase,
        *,
        interval_sec: float,
        sync_idle_sec: float,
        batch: int = 10,
    ) -> None:
        self._publish = publish
        self._sync = sync
        self._interval = interval_sec
        self._sync_idle = sync_idle_sec
        self._batch = batch
        self._stop = asyncio.Event()
        self._last_publish_at: float = 0.0

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        while not self._stop.is_set():
            try:
                count = self._publish.execute(batch=self._batch)
                now = time.monotonic()
                if count > 0:
                    self._last_publish_at = now
                if (
                    self._last_publish_at > 0
                    and now - self._last_publish_at >= self._sync_idle
                ):
                    self._sync.execute()
                    self._last_publish_at = 0.0
            except Exception:
                log.exception("worker tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval)
            except asyncio.TimeoutError:
                pass
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/worker/test_background.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/briefing/worker tests/worker
git commit -m "feat(worker): BackgroundWorker"
```

---

### Task 5.2: Composition Root (`interface/app.py`)

**Files:**
- Create: `src/briefing/interface/app.py`
- Create: `tests/interface/test_app.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/interface/test_app.py
import os

from fastapi.testclient import TestClient

from briefing.interface.app import create_app
from briefing.interface.settings import Settings


def test_create_app_smoke(tmp_path, monkeypatch):
    monkeypatch.setenv("BRIEFING_DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.setenv("BRIEFING_VAULT_PATH", str(tmp_path / "vault"))
    (tmp_path / "vault").mkdir()
    monkeypatch.setenv("BRIEFING_STOPWORDS_PATH", "data/stopwords.txt")
    monkeypatch.setenv("BRIEFING_ADMIN_USER", "u")
    monkeypatch.setenv("BRIEFING_ADMIN_PASSWORD", "p")
    monkeypatch.setenv("BRIEFING_LOG_PATH", str(tmp_path / "x.log"))

    app = create_app(Settings(), start_worker=False)
    c = TestClient(app)

    r = c.post("/webhook/dooray", json={"text": "통합 테스트 메시지입니다."})
    assert r.status_code == 200

    r2 = c.get("/admin", auth=("u", "p"))
    assert r2.status_code == 200
```

- [ ] **Step 2: 실패 확인**

```powershell
pytest tests/interface/test_app.py -v
```

Expected: ImportError.

- [ ] **Step 3: 구현**

```python
# src/briefing/interface/app.py
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from briefing.application.admin_queries import AdminQueries
from briefing.application.ingest_article import IngestArticleUseCase
from briefing.application.publish_pending import PublishPendingUseCase
from briefing.application.replay_failed import ReplayFailedUseCase
from briefing.application.sync_vault import SyncVaultUseCase
from briefing.infrastructure.nlp.kiwi_extractor import KiwiKeywordExtractor
from briefing.infrastructure.persistence.connection import open_connection
from briefing.infrastructure.persistence.schema import migrate
from briefing.infrastructure.persistence.sqlite_article_repo import SqliteArticleRepository
from briefing.infrastructure.sources.dooray import DoorayAdapter
from briefing.infrastructure.sources.registry import SourceRegistry
from briefing.infrastructure.sync.git_sync import GitVaultSync
from briefing.infrastructure.vault.markdown_publisher import MarkdownVaultPublisher
from briefing.interface.admin.auth import build_admin_auth_dependency
from briefing.interface.admin.routes import build_admin_router
from briefing.interface.settings import Settings
from briefing.interface.webhook.routes import build_webhook_router
from briefing.worker.background import BackgroundWorker

TEMPLATES_DIR = Path(__file__).parent / "admin" / "templates"


def _configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def create_app(settings: Settings | None = None, *, start_worker: bool = True) -> FastAPI:
    settings = settings or Settings()
    _configure_logging(settings.log_path)

    # infra
    conn = open_connection(settings.db_path)
    migrate(conn)
    repo = SqliteArticleRepository(conn)
    extractor = KiwiKeywordExtractor(
        stopwords_path=settings.stopwords_path, top_n=settings.keyword_top_n
    )
    publisher = MarkdownVaultPublisher(settings.vault_path)
    sync = GitVaultSync(
        settings.vault_path, remote=settings.git_remote, branch=settings.git_branch
    )

    sources = SourceRegistry()
    sources.register(DoorayAdapter(token=settings.dooray_token))

    # use cases
    ingest = IngestArticleUseCase(repo)
    publish = PublishPendingUseCase(repo, extractor, publisher, max_retry=settings.max_retry)
    sync_uc = SyncVaultUseCase(repo, sync)
    replay = ReplayFailedUseCase(repo)
    queries = AdminQueries(repo, sync)

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    require_admin = build_admin_auth_dependency(settings.admin_user, settings.admin_password)
    worker = BackgroundWorker(
        publish,
        sync_uc,
        interval_sec=settings.worker_interval_sec,
        sync_idle_sec=settings.sync_idle_sec,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if start_worker:
            task = asyncio.create_task(worker.run())
        try:
            yield
        finally:
            worker.stop()
            if task:
                await task

    app = FastAPI(lifespan=lifespan)
    app.include_router(build_webhook_router(sources, ingest))
    app.include_router(
        build_admin_router(
            templates=templates,
            queries=queries,
            sync_use_case=sync_uc,
            replay_use_case=replay,
            sources=sources,
            log_path=settings.log_path,
            require_admin=require_admin,
        )
    )
    return app
```

- [ ] **Step 4: 통과 확인**

```powershell
pytest tests/interface/test_app.py -v
```

Expected: 1 passed.

- [ ] **Step 5: 전체 테스트 실행**

```powershell
pytest -v
```

Expected: 모든 테스트 통과.

- [ ] **Step 6: Commit**

```powershell
git add src/briefing/interface/app.py tests/interface/test_app.py
git commit -m "feat(interface): composition root (create_app)"
```

---

## Phase 6: End-to-End 검증 + 문서

### Task 6.1: End-to-End 통합 테스트

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_e2e.py
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from git import Repo

from briefing.interface.app import create_app
from briefing.interface.settings import Settings


def _setup_remote(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    Repo.init(remote, bare=True)
    vault = tmp_path / "vault"
    repo = Repo.init(vault)
    repo.git.checkout("-b", "main")
    repo.git.commit("--allow-empty", "-m", "init")
    repo.create_remote("origin", str(remote))
    repo.git.push("--set-upstream", "origin", "main")
    return vault, remote


def test_e2e_webhook_to_vault_to_push(tmp_path, monkeypatch):
    vault, remote = _setup_remote(tmp_path)
    monkeypatch.setenv("BRIEFING_DB_PATH", str(tmp_path / "x.db"))
    monkeypatch.setenv("BRIEFING_VAULT_PATH", str(vault))
    monkeypatch.setenv("BRIEFING_STOPWORDS_PATH", "data/stopwords.txt")
    monkeypatch.setenv("BRIEFING_ADMIN_USER", "u")
    monkeypatch.setenv("BRIEFING_ADMIN_PASSWORD", "p")
    monkeypatch.setenv("BRIEFING_LOG_PATH", str(tmp_path / "x.log"))
    monkeypatch.setenv("BRIEFING_WORKER_INTERVAL_SEC", "0")
    monkeypatch.setenv("BRIEFING_SYNC_IDLE_SEC", "0")

    settings = Settings()
    app = create_app(settings, start_worker=False)
    client = TestClient(app)

    with client:  # lifespan 실행
        r = client.post(
            "/webhook/dooray",
            json={
                "text": "네이버가 새로운 AI 반도체를 발표했습니다. 자세한 내용은 링크를 참조하세요.",
                "attachments": [{"title": "네이버 AI 반도체", "titleLink": "https://example.com"}],
            },
        )
        assert r.status_code == 200

        # 수동으로 worker tick
        r2 = client.post("/admin/sync/push", auth=("u", "p"))
        # 수동 push 전에 publish가 한 번 돌아야 하므로, 워커 비활성 환경에서는
        # admin replay 트리거로 비동기 처리 대신 직접 call:
        from briefing.application.publish_pending import PublishPendingUseCase
        from briefing.infrastructure.nlp.kiwi_extractor import KiwiKeywordExtractor
        from briefing.infrastructure.persistence.connection import open_connection
        from briefing.infrastructure.persistence.schema import migrate
        from briefing.infrastructure.persistence.sqlite_article_repo import (
            SqliteArticleRepository,
        )
        from briefing.infrastructure.vault.markdown_publisher import (
            MarkdownVaultPublisher,
        )

        conn = open_connection(settings.db_path)
        migrate(conn)
        repo_for_check = SqliteArticleRepository(conn)
        pub_uc = PublishPendingUseCase(
            repo_for_check,
            KiwiKeywordExtractor(stopwords_path=settings.stopwords_path),
            MarkdownVaultPublisher(settings.vault_path),
            max_retry=3,
        )
        assert pub_uc.execute(batch=10) == 1

        r3 = client.post("/admin/sync/push", auth=("u", "p"))
        assert r3.status_code == 200 and r3.json()["ok"] is True

    # vault에 파일 생성 확인
    files = list((vault / "dooray").glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "네이버" in content
    assert "#" in content  # 태그 부착
```

- [ ] **Step 2: 통과 확인**

```powershell
pytest tests/test_e2e.py -v
```

Expected: 1 passed.

- [ ] **Step 3: Commit**

```powershell
git add tests/test_e2e.py
git commit -m "test: end-to-end webhook → vault → push"
```

---

### Task 6.2: README 보강 + 운영 가이드

**Files:**
- Modify: `README.md`

- [ ] **Step 1: README 갱신**

```markdown
# Briefing

Dooray incoming webhook으로 들어오는 메시지를 한국어 키워드 태깅과 함께 Obsidian vault markdown으로 자동 적재합니다.

Spec: `docs/superpowers/specs/2026-05-13-briefing-design.md`
Plan: `docs/superpowers/plans/2026-05-13-briefing-implementation.md`

## Architecture

- **DDD 4-layer**: `domain` (entities, ports) → `application` (use cases) → `infrastructure` (sqlite/kiwi/git/dooray) → `interface` (FastAPI + Jinja2/HTMX admin)
- **Extensibility**: 신규 source 추가는 `SourceAdapter` 구현 + `SourceRegistry.register` 한 줄
- **Background worker**: asyncio 단일 태스크. 5초 간격으로 pending 처리, 60초 idle 후 git push

## Setup

### 서버측 (briefing 서비스)

```powershell
git clone <this repo>
cd briefing
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# .env 편집: vault path, admin password, git remote 등
uvicorn briefing.interface.app:create_app --factory --host 0.0.0.0 --port 8000
```

### 서버측 vault 초기화

`BRIEFING_VAULT_PATH`로 지정한 폴더를 git repo로 만들고 원격 push 권한 설정:

```powershell
git init <vault>
cd <vault>
git checkout -b main
git remote add origin git@github.com:me/brief-vault.git
git config user.name "briefing-bot"
git config user.email "briefing@example.com"
git commit --allow-empty -m "init"
git push -u origin main
```

### 로컬 (Obsidian vault)

기존 vault 안에 `08.News/brief/` 폴더를 별도 git clone:

```powershell
cd "<your-vault>\08.News"
git clone git@github.com:me/brief-vault.git brief
```

OS 스케줄러로 주기적 pull 설정 (Windows Task Scheduler 예시):

```powershell
# 5분마다 실행되는 작업 등록
$action = New-ScheduledTaskAction -Execute "git" `
  -Argument "-C `"$HOME\Obsidian\Vault\08.News\brief`" pull --ff-only" `
  -WorkingDirectory "$HOME\Obsidian\Vault\08.News\brief"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
  -RepetitionInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "briefing-pull" -Action $action -Trigger $trigger
```

## Dooray 설정

두레이 채널의 incoming webhook URL을 `https://<your-server>/webhook/dooray`로 지정.
서명 검증을 사용하려면 `BRIEFING_DOORAY_TOKEN` 환경변수 설정 + 두레이 webhook 헤더에 동일 토큰 사용.

## Admin UI

`http://<your-server>:8000/admin` (Basic Auth, `BRIEFING_ADMIN_USER`/`BRIEFING_ADMIN_PASSWORD`).

화면:
- `/admin` 대시보드
- `/admin/articles` 수신 내역 목록 + 필터/검색
- `/admin/articles/{id}` 상세 + 재시도
- `/admin/sync` 동기화 상태 + 수동 push
- `/admin/sources` 등록 source 목록
- `/admin/logs` 로그 tail

## Extending: 새 source 추가

1. `src/briefing/infrastructure/sources/<name>.py`에 `SourceAdapter` 구현
2. `interface/app.py`의 `sources.register(...)`에 한 줄 추가

domain/application 코드는 무수정.

## Test

```powershell
pytest -v
```
```

- [ ] **Step 2: Commit**

```powershell
git add README.md
git commit -m "docs: setup, operations, and extension guide"
```

---

## 부록: 디렉토리 리네임 (마지막 단계)

본 plan 실행이 끝나고, 모든 테스트가 통과한 후에 수행한다. 현재 세션에서 직접 수행하지 말고, 사용자가 직접 PowerShell에서 실행:

```powershell
cd E:\private-projects
Move-Item -Path .\getNews -Destination .\briefing
```

이후 새 세션을 열고 `E:\private-projects\briefing`에서 작업을 이어간다.

---

## Implementation Order Summary

| Phase | Tasks | 목적 |
|---|---|---|
| 0 | 0.1-0.3 | git/패키지/pytest 부트스트랩 |
| 1 | 1.1-1.4 | domain (의존성 없음) |
| 2 | 2.1-2.5 | application (fake port 사용) |
| 3 | 3.1-3.6 | infrastructure 구현체 |
| 4 | 4.1-4.4 | webhook + admin UI |
| 5 | 5.1-5.2 | worker + composition root |
| 6 | 6.1-6.2 | e2e + docs |

각 phase는 직전 phase에 의존. 같은 phase 내 task는 보통 독립적이라 순서 무관하지만, 본 plan은 위→아래 순서로 진행 권장.
