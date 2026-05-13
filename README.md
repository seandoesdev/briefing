# Briefing

Dooray incoming webhook으로 들어오는 메시지를 한국어 키워드 태깅과 함께 Obsidian vault markdown으로 자동 적재합니다.

- Spec: `docs/superpowers/specs/2026-05-13-briefing-design.md`
- Plan: `docs/superpowers/plans/2026-05-13-briefing-implementation.md`

## Architecture

- **DDD 4-layer**: `domain` (entities, ports) → `application` (use cases) → `infrastructure` (sqlite/kiwi/git/dooray) → `interface` (FastAPI + Jinja2/HTMX admin)
- **Extensibility**: 신규 source 추가는 `SourceAdapter` 구현 + `SourceRegistry.register` 한 줄
- **Background worker**: asyncio 단일 태스크. 5초 간격으로 pending 처리, 60초 idle 후 git push

## Setup

### Option A: Docker (권장)

`docker compose`로 한 번에 띄우는 방식. SQLite DB·로그는 `briefing-runtime` 볼륨에, 서버측 vault git repo는 `briefing-vault` 볼륨에 보관됨.

```bash
# 1. 환경변수 설정 (.env 파일 또는 셸 export)
#    필수: BRIEFING_ADMIN_PASSWORD
#    선택: BRIEFING_GIT_REMOTE_URL (지정 시 entrypoint가 vault에 remote 자동 등록)
#          BRIEFING_DOORAY_TOKEN, BRIEFING_ADMIN_USER 등
cat > .env <<'EOF'
BRIEFING_ADMIN_USER=admin
BRIEFING_ADMIN_PASSWORD=change-me
BRIEFING_DOORAY_TOKEN=
BRIEFING_GIT_REMOTE_URL=git@github.com:me/brief-vault.git
BRIEFING_GIT_USER_NAME=briefing-bot
BRIEFING_GIT_USER_EMAIL=briefing@example.com
EOF

# 2. 빌드 + 기동
docker compose up -d --build

# 3. 로그 확인
docker compose logs -f briefing

# 4. 접속
#    Webhook:  http://localhost:8000/webhook/dooray
#    Admin UI: http://localhost:8000/admin  (Basic Auth)
```

**Git push 인증**: compose 파일은 `${HOME}/.ssh`를 컨테이너의 `/home/briefing/.ssh`로 read-only 마운트합니다. SSH 키가 다른 위치에 있거나 인증이 필요 없으면 해당 volumes 항목을 제거/수정하세요. Windows에서는 Docker Desktop이 자동으로 호스트 경로를 변환합니다.

**Vault 초기 push 테스트**:

```bash
docker compose exec briefing git -C /app/vault push -u origin main
```

이후부터는 briefing이 알아서 60초 idle마다 자동 push.

**컨테이너 안에서 git remote 수동 등록** (compose에 URL 안 넣었을 때):

```bash
docker compose exec briefing git -C /app/vault remote add origin git@github.com:me/brief-vault.git
```

### Option B: 로컬 직접 실행

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

## Layout

- `src/briefing/domain/` — pure domain (entities, value objects, ports)
- `src/briefing/application/` — use cases
- `src/briefing/infrastructure/` — concrete adapters (sqlite, kiwi, git, dooray)
- `src/briefing/interface/` — FastAPI app + admin UI
- `src/briefing/worker/` — background asyncio worker

## Test

```powershell
pytest -v
```
