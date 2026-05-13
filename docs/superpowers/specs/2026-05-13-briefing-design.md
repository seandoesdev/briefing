# Briefing — 두레이 incoming → Obsidian Vault 자동 적재 시스템

- **상태**: Draft v1
- **작성일**: 2026-05-13
- **프로젝트명**: `briefing`
- **대상 디렉토리**: `E:/private-projects/getNews` → `briefing`로 리네임 예정

---

## 1. 목적

두레이(Dooray) incoming webhook으로 수신되는 메시지/메일/업무 알림 등 다양한 종류의 정보를 자동으로 옵시디언 볼트 내 지정 폴더(`08.News/brief/`)에 정리해 적재한다. 향후 두레이 외의 source(RSS, 웹 스크래핑, 수동 등)를 추가할 수 있도록 확장 가능한 구조로 설계하되, **1차 구현 범위는 두레이만**으로 한다.

## 2. 핵심 결정사항 (요약)

| 항목 | 결정 |
|---|---|
| 처리 범위 | 두레이 incoming의 모든 종류(메신저/메일/업무/raw payload) |
| 1차 source | **두레이만**. 다른 source는 확장 포인트만 제공하고 구현은 미래 |
| Vault 저장 단위 | 소스/카테고리 폴더 + 일자별 누적 markdown 파일 |
| 연관성(링크) | 한국어 형태소 분석(Kiwi) 기반 키워드를 `#태그`로 부착 → 옵시디언 자체 태그 그래프로 자동 연결 |
| 동기화 구조 | 원격 서버가 git push → 로컬이 git pull |
| 동기화 범위 | 볼트 전체가 아닌 **`08.News/brief/` 하위만 별도 git repo** |
| 로컬 pull 방법 | Obsidian Git 플러그인(볼트 루트 가정)이 부적합 → 별도 OS 스케줄러(cron / Windows Task Scheduler / systemd timer)에서 `git pull` |
| 중복 처리 | payload 해시 기반 멱등성 (SQLite UNIQUE 제약) |
| 아키텍처 | DDD 4-레이어(domain/application/infrastructure/interface) **가볍게**. CQRS/Event Sourcing 미적용 |
| 큐 | 인-프로세스 asyncio worker + SQLite를 큐 겸 저장소로 사용 |
| Admin UI | Jinja2 + HTMX, Basic Auth |

## 3. 시스템 컨텍스트

```
                    ┌────────────────────┐
   두레이 채널 ────▶│  briefing 서비스    │
   (incoming hook)  │  (원격 서버)        │
                    │  - FastAPI         │
                    │  - SQLite          │
                    │  - vault/(작업본)  │
                    │  - git push        │
                    └─────────┬──────────┘
                              │ push
                              ▼
                    ┌────────────────────┐
                    │  원격 Git Repo      │
                    │  (GitHub private   │
                    │   또는 self-host)  │
                    └─────────┬──────────┘
                              │ pull (스케줄러)
                              ▼
                    ┌────────────────────────────┐
                    │  로컬 PC                    │
                    │  Obsidian Vault/           │
                    │   01.../                   │
                    │   02.../                   │
                    │   ...                      │
                    │   08.News/brief/  ◀──── git repo
                    └────────────────────────────┘
```

**사용자가 별도 세팅하는 항목** (briefing 코드 범위 밖)
- 원격 서버(VPS/홈서버) 및 도메인/방화벽
- Private Git remote 1개 (GitHub/Gitea 등) + 서버 SSH 키 등록
- 로컬 `08.News/brief/`를 위 remote의 clone으로 초기화
- 로컬 OS 스케줄러에 N분마다 `git -C <vault>/08.News/brief pull --ff-only` 등록
- 두레이 incoming webhook URL을 briefing 서버로 지정

## 4. 도메인 모델

### 4.1 엔티티 / 값 객체

```python
# domain/value_objects.py
SourceName       = NewType("SourceName", str)        # 'dooray', 미래: 'rss' 등
PayloadHash      = NewType("PayloadHash", str)       # SHA-256 hex
ArticleId        = NewType("ArticleId", str)         # UUIDv4
Tag              = NewType("Tag", str)

class ArticleStatus(StrEnum):
    RECEIVED  = "received"     # webhook 수신, 저장됨
    PROCESSED = "processed"    # 키워드 추출 + vault 파일 작성 완료
    PUBLISHED = "published"    # git commit/push 완료
    FAILED    = "failed"       # 영구 실패 (재시도 한도 초과)
```

```python
# domain/entities.py
@dataclass
class Article:
    id:            ArticleId
    source:        SourceName
    external_id:   str | None         # 두레이 message id 등
    payload_hash:  PayloadHash
    received_at:   datetime
    title:         str
    body:          str
    url:           str | None
    tags:          list[Tag]
    raw_payload:   dict
    status:        ArticleStatus
    output_path:   Path | None        # vault 내 어느 .md 파일에 들어갔는지
    error:         str | None
    retry_count:   int
```

### 4.2 포트 (추상 인터페이스)

```python
# domain/ports.py — 모든 외부 의존성 추상화. application은 이것만 알면 됨.

class SourceAdapter(Protocol):
    """신규 source 추가 시 이 하나만 구현."""
    name: SourceName
    def parse(self, raw_payload: dict) -> Article: ...
    def verify(self, headers: dict, raw_body: bytes) -> bool:
        """선택: 서명/secret 검증. 미지원 source는 항상 True"""

class KeywordExtractor(Protocol):
    def extract(self, text: str) -> list[Tag]: ...

class ArticleRepository(Protocol):
    def save(self, article: Article) -> None: ...
    def find_by_hash(self, h: PayloadHash) -> Article | None: ...
    def find_by_id(self, id: ArticleId) -> Article | None: ...
    def list_pending(self, limit: int) -> list[Article]: ...
    def list_for_admin(self, filters: AdminFilter) -> list[Article]: ...
    def update_status(self, id: ArticleId, status: ArticleStatus,
                      output_path: Path | None = None,
                      error: str | None = None) -> None: ...

class VaultPublisher(Protocol):
    def publish(self, article: Article) -> Path:
        """vault에 .md 파일 생성/append. 출력 경로 반환."""

class VaultSync(Protocol):
    def commit_and_push(self, message: str) -> SyncResult: ...
    def status(self) -> SyncStatus: ...
```

### 4.3 유즈케이스 (application 레이어)

| 유즈케이스 | 트리거 | 책임 |
|---|---|---|
| `IngestArticle` | webhook 수신 | adapter.parse → 멱등성 검사 → repo.save(status=RECEIVED) |
| `PublishPending` | worker tick (5s) | 미처리 article에 대해 키워드 추출 → vault 작성 → status=PROCESSED |
| `SyncVault` | idle 60s 또는 수동 | git add/commit/push → status=PUBLISHED + sync_log 기록 |
| `ReplayFailed` | admin 액션 | 실패 article을 RECEIVED로 되돌려 재처리 |
| `AdminQueries` | admin UI 조회 | 대시보드 통계, 목록 필터, 로그 조회 (read 전용) |

## 5. 인프라스트럭처 구현

### 5.1 DoorayAdapter (`infrastructure/sources/dooray.py`)
- 두레이 incoming webhook payload(JSON)를 받아 `Article`로 변환
- 필드 매핑:
  - `title`: payload의 `attachments[0].title` 또는 `text` 첫 줄
  - `body`: `attachments[*].text` 합치기 또는 `text` 본문
  - `url`: `attachments[0].titleLink`
  - `external_id`: 두레이가 제공하는 메시지 ID (없으면 None)
- `verify`: `BRIEFING_DOORAY_TOKEN` 설정 시 헤더 검증, 아니면 True

### 5.2 KiwiKeywordExtractor (`infrastructure/nlp/kiwi_extractor.py`)
- `kiwipiepy`로 명사 추출
- 불용어 사전(`data/stopwords.txt`)으로 필터링
- 빈도 상위 N개(기본 5) 반환
- 영어/숫자 토큰은 길이 ≥ 2일 때만 포함

### 5.3 SqliteArticleRepository (`infrastructure/persistence/sqlite_article_repo.py`)
- 단일 SQLite DB (`data/briefing.db`)
- 스키마는 §6 참조
- 트랜잭션 단위로 save/update
- 마이그레이션: 기동 시 `PRAGMA user_version`으로 버전 체크 후 적용

### 5.4 MarkdownVaultPublisher (`infrastructure/vault/markdown_publisher.py`)
- 출력 경로: `<vault_root>/<source>/<YYYY-MM-DD>.md`
  - 예: `vault/dooray/2026-05-13.md`
- 파일 없으면 생성(상단에 일자 헤더), 있으면 append
- 1건 markdown 포맷:
  ```markdown
  ## 14:32 — 기사 제목
  **source**: dooray · **tags**: #네이버 #AI #반도체
  **url**: https://...

  본문 텍스트...

  ---
  ```
- 파일 락(`fcntl` / Windows `msvcrt`) 또는 단일 worker 보장으로 동시 쓰기 방지

### 5.5 GitVaultSync (`infrastructure/sync/git_sync.py`)
- `gitpython` 사용
- `commit_and_push(message)`: `git add . && git commit -m <msg> && git push origin <branch>`
- 변경 사항 없으면 no-op
- push 실패 시 sync_log에 기록 후 다음 사이클 재시도
- conflict 발생 시 자동 해결 시도하지 않음 — 상태만 기록, admin UI 알림

### 5.6 SourceRegistry (`infrastructure/sources/registry.py`)
```python
class SourceRegistry:
    def register(self, adapter: SourceAdapter) -> None: ...
    def get(self, name: SourceName) -> SourceAdapter | None: ...
    def list_all(self) -> list[SourceAdapter]: ...
```
신규 source 추가 = 어댑터 작성 + `register()` 1줄.

## 6. 데이터 모델 (SQLite)

```sql
CREATE TABLE articles (
  id            TEXT PRIMARY KEY,                  -- UUIDv4
  source        TEXT NOT NULL,                     -- 'dooray' (확장 시 추가)
  external_id   TEXT,
  payload_hash  TEXT UNIQUE NOT NULL,              -- 멱등성
  received_at   TIMESTAMP NOT NULL,
  title         TEXT NOT NULL,
  body          TEXT NOT NULL,
  url           TEXT,
  raw_payload   TEXT NOT NULL,                     -- JSON 원본
  status        TEXT NOT NULL,                     -- ArticleStatus 값
  output_path   TEXT,
  error         TEXT,
  retry_count   INTEGER NOT NULL DEFAULT 0,
  processed_at  TIMESTAMP,
  published_at  TIMESTAMP
);
CREATE INDEX idx_articles_status   ON articles(status);
CREATE INDEX idx_articles_source   ON articles(source);
CREATE INDEX idx_articles_received ON articles(received_at);

CREATE TABLE article_tags (
  article_id  TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  tag         TEXT NOT NULL,
  PRIMARY KEY (article_id, tag)
);
CREATE INDEX idx_article_tags_tag ON article_tags(tag);

CREATE TABLE sync_log (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  pushed_at     TIMESTAMP NOT NULL,
  commit_sha    TEXT,
  article_count INTEGER,
  status        TEXT NOT NULL,                     -- 'success' | 'failed'
  error         TEXT
);

CREATE TABLE parse_failures (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  source       TEXT NOT NULL,
  received_at  TIMESTAMP NOT NULL,
  raw_payload  TEXT NOT NULL,                      -- JSON
  error        TEXT NOT NULL,
  resolved     INTEGER NOT NULL DEFAULT 0          -- 0|1
);
```

## 7. HTTP 인터페이스

### 7.1 Webhook
- `POST /webhook/{source}` — `source` path param으로 `SourceRegistry.get()` 조회
- 등록 안 된 source는 404
- 응답은 항상 200 (멱등성 skip 포함). payload 자체가 비어있을 때만 400
- 실제 1차 구현 라우트: `POST /webhook/dooray`

### 7.2 Admin UI (Jinja2 + HTMX)

| 경로 | 메서드 | 기능 |
|---|---|---|
| `/admin` | GET | 대시보드: 오늘/이번주 수집 수, source별 통계, 워커 상태, 마지막 push 시각 |
| `/admin/articles` | GET | 목록 (필터: source, 날짜, 상태, 태그) + 검색. HTMX 페이지네이션 |
| `/admin/articles/{id}` | GET | 상세: raw payload, 생성 markdown, 태그 |
| `/admin/articles/{id}/retry` | POST | 재시도 트리거 |
| `/admin/articles/{id}/delete` | POST | 삭제 (markdown 파일은 보존, DB만 제거) |
| `/admin/sync` | GET | 최근 sync_log, 마지막 commit_sha, 미푸시 건수 |
| `/admin/sync/push` | POST | 수동 push 트리거 |
| `/admin/sources` | GET | 등록 source 목록, 각 source 누적 통계 |
| `/admin/logs` | GET | 구조화 로그 뷰어 (레벨/시간/request_id 필터) |
| `/admin/replay` | POST | 실패 article 일괄 재처리 |

- 모든 `/admin/*`은 HTTP Basic Auth (`BRIEFING_ADMIN_USER`, `BRIEFING_ADMIN_PASSWORD`)
- 로그: 구조화 JSON 로그(`structlog` 또는 stdlib JSON formatter)를 `data/briefing.log`에 회전 저장, `/admin/logs`에서 tail 조회

## 8. 백그라운드 워커

- FastAPI `lifespan`에서 단일 asyncio 태스크로 기동
- 루프(5초 간격):
  1. `PublishPending.run(batch=10)` — RECEIVED 건들 처리
  2. 마지막 publish로부터 60초 idle이면 `SyncVault.run()` 호출
- 종료 시 graceful shutdown (현재 작업 마무리 후 exit)

**재시도 정책**
- 단계 실패 시 `retry_count++`, `status=RECEIVED` 유지
- `retry_count ≥ 3` 시 `status=FAILED` (영구 실패)
- `ReplayFailed`로만 부활 가능

## 9. 에러 처리 정책

| 발생 지점 | 동작 |
|---|---|
| webhook 본문 파싱 실패 | 400 응답, 로그 기록, DB 미저장 |
| 멱등성 hit | 200 + `{"status": "duplicate"}`, 로그 debug |
| adapter.parse 실패 | webhook은 항상 200 반환 (두레이 재시도 폭주 방지). 원본 payload는 별도 `parse_failures` 테이블에 저장 (raw_payload + error). admin UI에서 조회/재처리 가능 |
| Kiwi 실패 | 빈 태그로 진행 (전체 실패 방지), warn 로그 |
| publisher 실패 | retry_count++, RECEIVED 유지 |
| git push 실패 | sync_log에 failed 기록, 다음 사이클 재시도. articles는 PROCESSED 상태 유지 |
| git conflict | 자동 해결 안 함. admin UI에 알림, 수동 개입 |

## 10. 설정 (.env)

```
# 서비스
BRIEFING_DB_PATH=/var/briefing/data/briefing.db
BRIEFING_VAULT_PATH=/var/briefing/vault          # 서버측 작업본 (git repo)
BRIEFING_LOG_PATH=/var/briefing/data/briefing.log

# Git
BRIEFING_GIT_REMOTE=git@github.com:me/brief-vault.git
BRIEFING_GIT_BRANCH=main
BRIEFING_GIT_USER_NAME=briefing-bot
BRIEFING_GIT_USER_EMAIL=briefing@example.com

# 워커
BRIEFING_WORKER_INTERVAL_SEC=5
BRIEFING_SYNC_IDLE_SEC=60
BRIEFING_MAX_RETRY=3

# 두레이
BRIEFING_DOORAY_TOKEN=                            # 비어있으면 검증 skip

# Admin
BRIEFING_ADMIN_USER=admin
BRIEFING_ADMIN_PASSWORD=<설정>

# NLP
BRIEFING_KEYWORD_TOP_N=5
BRIEFING_STOPWORDS_PATH=data/stopwords.txt
```

## 11. 의존성

| 라이브러리 | 용도 |
|---|---|
| `fastapi`, `uvicorn` | HTTP 서버 |
| `jinja2`, `python-multipart` | Admin UI 템플릿 |
| `pydantic`, `pydantic-settings` | 검증/설정 |
| `kiwipiepy` | 한국어 형태소 |
| `gitpython` | git 조작 |
| `structlog` (선택) | 구조화 로그 |
| 표준 라이브러리 | `sqlite3`, `asyncio`, `hashlib`, `pathlib`, `secrets` |

## 12. 테스트 전략

- **domain**: 순수 단위 테스트. 외부 의존성 없음.
- **application**: 포트를 fake로 주입한 시나리오 테스트 (IngestArticle 멱등성, PublishPending 재시도, SyncVault no-op 등).
- **infrastructure**:
  - `sqlite_article_repo`: in-memory sqlite로 통합
  - `kiwi_extractor`: 실제 Kiwi 스모크
  - `markdown_publisher`: `tmp_path`
  - `git_sync`: `tmp_path`에 bare repo 만들어 통합
- **interface**: FastAPI `TestClient`로 webhook + admin 라우트 통합

## 13. 디렉토리 구조 (최종)

```
briefing/                                # 프로젝트 루트 (현재 getNews에서 리네임)
├── src/briefing/
│   ├── domain/
│   │   ├── entities.py
│   │   ├── value_objects.py
│   │   ├── events.py
│   │   └── ports.py
│   ├── application/
│   │   ├── ingest_article.py
│   │   ├── publish_pending.py
│   │   ├── sync_vault.py
│   │   ├── replay_failed.py
│   │   └── admin_queries.py
│   ├── infrastructure/
│   │   ├── sources/
│   │   │   ├── dooray.py
│   │   │   └── registry.py
│   │   ├── persistence/
│   │   │   └── sqlite_article_repo.py
│   │   ├── nlp/
│   │   │   └── kiwi_extractor.py
│   │   ├── vault/
│   │   │   └── markdown_publisher.py
│   │   └── sync/
│   │       └── git_sync.py
│   ├── interface/
│   │   ├── app.py                       # composition root (DI 와이어링)
│   │   ├── webhook/routes.py
│   │   ├── api/routes.py
│   │   └── admin/
│   │       ├── routes.py
│   │       └── templates/
│   │           ├── base.html
│   │           ├── dashboard.html
│   │           ├── articles_list.html
│   │           ├── article_detail.html
│   │           ├── sync.html
│   │           ├── sources.html
│   │           └── logs.html
│   └── worker/
│       └── background.py
├── tests/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── interface/
├── data/                                # gitignore (런타임 산출물)
│   ├── briefing.db
│   ├── briefing.log
│   └── stopwords.txt
├── docs/
│   └── superpowers/specs/2026-05-13-briefing-design.md  # 본 문서
├── .env.example
├── pyproject.toml
└── README.md
```

## 14. 확장 시나리오 검증

### 미래: RSS 피드 수집 추가
1. `infrastructure/sources/rss.py`에 `class RssAdapter(SourceAdapter)` 작성
2. `interface/app.py`에 `sources.register(RssAdapter(...))` 1줄
3. RSS는 webhook이 아니라 polling이므로 `application/poll_sources.py` 유즈케이스와 worker 스케줄 hook 추가

→ domain/application 핵심 로직 **무수정**, publisher/sync/admin UI **무수정**.

### 미래: 다른 키워드 추출기 (LLM 기반 등)
1. `infrastructure/nlp/llm_extractor.py`에 `class LlmKeywordExtractor(KeywordExtractor)` 작성
2. `interface/app.py`에서 주입 라인 교체

→ application은 `KeywordExtractor` 포트만 보므로 무수정.

## 15. 1차 구현 범위 (Scope)

**In Scope**
- 두레이 webhook 수신 + 멱등성
- Kiwi 키워드 추출
- 일자별 markdown 작성
- 서버측 git commit/push
- Admin UI 7개 화면 전부
- 구조화 로그 + admin 로그 뷰어
- 단위/통합 테스트

**Out of Scope (미래)**
- 두레이 외 source 어댑터 (포트만 제공)
- LLM 기반 키워드 추출
- 다중 vault 지원
- 로컬 PC측 sync 도구 (사용자가 OS 스케줄러로 별도 세팅)
- 멀티 사용자/RBAC (admin은 단일 계정 basic auth)

## 16. 디렉토리 리네임

`E:/private-projects/getNews` → `E:/private-projects/briefing`은 spec 승인 후 구현 계획 작성 직전에 1회 수행한다.
