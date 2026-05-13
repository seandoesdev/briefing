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
        recent = queries.list_articles(AdminFilter(limit=8, offset=0))
        return templates.TemplateResponse(
            request, "dashboard.html", {"summary": summary, "recent": recent}
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
            request, "articles_list.html", {"items": items, "filter": f}
        )

    @router.get("/admin/articles/{id}", response_class=HTMLResponse, dependencies=[auth_dep])
    def article_detail(request: Request, id: str):
        a = queries.get_article(id)
        if a is None:
            raise HTTPException(404)
        return templates.TemplateResponse(request, "article_detail.html", {"a": a})

    @router.post("/admin/articles/{id}/retry", dependencies=[auth_dep])
    def article_retry(id: str):
        replay_use_case.execute(article_id=id)
        return RedirectResponse(url=f"/admin/articles/{id}", status_code=303)

    @router.get("/admin/sync", response_class=HTMLResponse, dependencies=[auth_dep])
    def sync_page(request: Request):
        summary = queries.dashboard()
        return templates.TemplateResponse(request, "sync.html", {"summary": summary})

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
        return templates.TemplateResponse(request, "sources.html", {"items": items})

    @router.get("/admin/logs", response_class=HTMLResponse, dependencies=[auth_dep])
    def logs_page(request: Request, tail: int = 200):
        if log_path.exists():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            lines = lines[-tail:]
        else:
            lines = []
        return templates.TemplateResponse(
            request, "logs.html", {"lines": lines, "tail": tail}
        )

    @router.post("/admin/replay", dependencies=[auth_dep])
    def replay_all():
        count = replay_use_case.execute()
        return {"replayed": count}

    return router
