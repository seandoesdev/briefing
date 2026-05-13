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
