# Briefing

Dooray incoming webhook으로 들어오는 메시지를 한국어 키워드 태깅과 함께 Obsidian vault markdown으로 자동 적재합니다.

- Spec: `docs/superpowers/specs/2026-05-13-briefing-design.md`
- Plan: `docs/superpowers/plans/2026-05-13-briefing-implementation.md`

## Architecture

- **DDD 4-layer**: `domain` (entities, ports) → `application` (use cases) → `infrastructure` (sqlite/kiwi/git/dooray) → `interface` (FastAPI + Jinja2/HTMX admin)
- **Extensibility**: 신규 source 추가는 `SourceAdapter` 구현 + `SourceRegistry.register` 한 줄
- **Background worker**: asyncio 단일 태스크. 5초 간격으로 pending 처리, 60초 idle 후 git push

## Quick Start (Docker)

전제: Docker 24+ / Docker Compose v2.

### 1. 환경변수 작성

프로젝트 루트에 `.env`:

```env
# 필수
BRIEFING_ADMIN_PASSWORD=change-me

# 선택 (지정 시 컨테이너 entrypoint가 vault에 자동으로 remote 등록)
BRIEFING_GIT_REMOTE_URL=git@github.com:me/brief-vault.git

# 선택
BRIEFING_ADMIN_USER=admin
BRIEFING_DOORAY_TOKEN=
BRIEFING_GIT_USER_NAME=briefing-bot
BRIEFING_GIT_USER_EMAIL=briefing@example.com
BRIEFING_KEYWORD_TOP_N=5
```

### 2. 빌드 + 기동

```bash
docker compose up -d --build
docker compose logs -f briefing
```

기동되면 다음 두 엔드포인트가 열립니다:

- `POST http://<host>:8000/webhook/dooray` — Dooray incoming webhook 수신
- `GET  http://<host>:8000/admin` — Admin UI (Basic Auth)

컨테이너 entrypoint가 첫 기동 시 `/app/vault`에 git repo를 init하고 `BRIEFING_GIT_REMOTE_URL`이 설정되어 있으면 remote도 자동으로 등록합니다.

### 3. 최초 1회 vault push

원격 git repo 인증이 되어있다면:

```bash
docker compose exec briefing git -C /app/vault push -u origin main
```

이후부터는 briefing 서비스가 60초 idle마다 자동으로 commit + push.

### 4. Dooray webhook 등록

Dooray 채널의 incoming webhook URL을 `http://<host>:8000/webhook/dooray`로 지정.
서명 검증을 쓰려면 `.env`에 `BRIEFING_DOORAY_TOKEN` 설정 + Dooray webhook 헤더에 동일 값 전달.

## 운영 (Docker)

| 작업 | 명령 |
|---|---|
| 로그 보기 | `docker compose logs -f briefing` |
| 재시작 | `docker compose restart briefing` |
| 정지 | `docker compose stop` |
| 컨테이너 셸 | `docker compose exec briefing sh` |
| 수동 push | `docker compose exec briefing git -C /app/vault push` |
| SQLite 직접 조회 | `docker compose exec briefing sqlite3 /app/runtime/briefing.db` |
| 이미지 재빌드 | `docker compose up -d --build` |
| 완전 초기화 | `docker compose down -v` (⚠ runtime/vault 볼륨 삭제) |

영속 볼륨:

- `briefing-runtime` — SQLite DB(`/app/runtime/briefing.db`) + 로그(`/app/runtime/briefing.log`)
- `briefing-vault` — 서버측 vault git repo (`/app/vault`)

### Git push 인증 (SSH)

`docker-compose.yml`은 호스트의 `${HOME}/.ssh`를 컨테이너 `/home/briefing/.ssh`로 read-only 마운트합니다.

- macOS/Linux: 그대로 동작.
- Windows: Docker Desktop이 `%USERPROFILE%\.ssh`를 자동 변환.
- SSH 키 위치가 다르거나 HTTPS+토큰을 쓰면 `volumes:` 항목을 환경에 맞게 수정.

`known_hosts`에 원격 호스트가 등록되어 있어야 합니다. 한 번:

```bash
docker compose exec briefing ssh-keyscan github.com >> /home/briefing/.ssh/known_hosts
```

(또는 호스트의 `~/.ssh/known_hosts`가 마운트되어 있으면 자동으로 사용됨)

## 로컬 Obsidian 연동

서버 vault git repo의 내용을 옵시디언 볼트 내 `08.News/brief/` 폴더로 받아옵니다.

### 1. 폴더 clone

```powershell
cd "<your-vault>\08.News"
git clone git@github.com:me/brief-vault.git brief
```

### 2. 주기적 pull 등록

옵시디언의 `Obsidian Git` 플러그인은 vault 루트만 관리하므로, 하위 폴더만 동기화하려면 OS 스케줄러를 사용합니다.

Windows Task Scheduler:

```powershell
$action = New-ScheduledTaskAction -Execute "git" `
  -Argument "-C `"$HOME\Obsidian\Vault\08.News\brief`" pull --ff-only" `
  -WorkingDirectory "$HOME\Obsidian\Vault\08.News\brief"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
  -RepetitionInterval (New-TimeSpan -Minutes 5)
Register-ScheduledTask -TaskName "briefing-pull" -Action $action -Trigger $trigger
```

macOS launchd / Linux cron:

```cron
*/5 * * * * git -C ~/Obsidian/Vault/08.News/brief pull --ff-only
```

## Admin UI

`http://<host>:8000/admin` (Basic Auth, `BRIEFING_ADMIN_USER`/`BRIEFING_ADMIN_PASSWORD`).

| 경로 | 기능 |
|---|---|
| `/admin` | 대시보드 (수집 수, source별 통계, 마지막 push) |
| `/admin/articles` | 수신 내역 목록 + 상태/태그/검색 필터 |
| `/admin/articles/{id}` | 상세 + 재시도 |
| `/admin/sync` | 동기화 상태 + 수동 push 버튼 |
| `/admin/sources` | 등록된 source 목록 |
| `/admin/logs` | 컨테이너 로그 tail |

## Extending: 새 source 추가

1. `src/briefing/infrastructure/sources/<name>.py`에 `SourceAdapter` 구현
2. `interface/app.py`의 `sources.register(...)`에 한 줄 추가
3. 이미지 재빌드: `docker compose up -d --build`

domain/application 코드는 무수정. webhook URL은 자동으로 `/webhook/<name>`이 활성화됨.

## Layout

- `src/briefing/domain/` — pure domain (entities, value objects, ports)
- `src/briefing/application/` — use cases
- `src/briefing/infrastructure/` — concrete adapters (sqlite, kiwi, git, dooray)
- `src/briefing/interface/` — FastAPI app + admin UI
- `src/briefing/worker/` — background asyncio worker
- `docker/entrypoint.sh` — 컨테이너 진입 시 vault git 초기화

## Development (Docker 없이 로컬 실행)

기여나 디버깅 목적으로 컨테이너 없이 직접 실행하려면:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env   # BRIEFING_VAULT_PATH 등을 로컬 경로로 수정
uvicorn briefing.interface.app:create_app --factory --reload
```

테스트 실행:

```powershell
pytest -v
```
