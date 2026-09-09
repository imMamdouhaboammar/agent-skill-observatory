from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .db import init_database, make_session_factory
from .catalog import catalog_stats
from .repository import list_skills


class SkillItem(BaseModel):
    canonical_key: str
    repo_full_name: str
    repo_url: str
    repo_default_branch: str
    path: str
    name: str
    description: str
    license: str | None
    compatibility: str | None
    stars: int
    forks: int
    pushed_at: str
    archived: bool
    discovery_source: str
    overall_score: int
    quality_score: int
    security_score: int
    maintenance_score: int
    adoption_score: int
    spec: dict[str, Any]
    security: dict[str, Any]
    resources: dict[str, Any]
    evidence: dict[str, Any]


class SkillList(BaseModel):
    items: list[SkillItem] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


def _serialize(record: Any) -> SkillItem:
    return SkillItem(
        canonical_key=record.canonical_key,
        repo_full_name=record.repo_full_name,
        repo_url=record.repo_url,
        repo_default_branch=record.repo_default_branch,
        path=record.path,
        name=record.name,
        description=record.description,
        license=record.license,
        compatibility=record.compatibility,
        stars=record.stars,
        forks=record.forks,
        pushed_at=record.pushed_at.isoformat(),
        archived=record.archived,
        discovery_source=record.discovery_source,
        overall_score=record.overall_score,
        quality_score=record.quality_score,
        security_score=record.security_score,
        maintenance_score=record.maintenance_score,
        adoption_score=record.adoption_score,
        spec=record.spec_json,
        security=record.security_json,
        resources=record.resources_json,
        evidence=record.evidence_json,
    )


def create_app(database_url: str | None = None) -> FastAPI:
    settings = Settings(database_url=database_url) if database_url else Settings()
    factory: sessionmaker[Session] = make_session_factory(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        init_database(settings.database_url)
        yield

    app = FastAPI(
        title="Agent Skill Observatory",
        version="0.1.0",
        description="Evidence-based index of open Agent Skills.",
        lifespan=lifespan,
    )

    def get_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/stats")
    def stats(session: Session = Depends(get_session)) -> dict[str, Any]:
        return catalog_stats(session)

    @app.get("/api/v1/skills", response_model=SkillList)
    def skills(
        session: Session = Depends(get_session),
        q: str | None = None,
        min_score: Annotated[int, Query(ge=0, le=100)] = 0,
        spec_valid: bool | None = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> SkillList:
        records, total = list_skills(
            session,
            query=q,
            min_score=min_score,
            spec_valid=spec_valid,
            limit=limit,
            offset=offset,
        )
        return SkillList(items=[_serialize(r) for r in records], total=total, limit=limit, offset=offset)

    web_dir = Path(__file__).resolve().parent / "web"
    if web_dir.is_dir():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

    return app


app = create_app()
