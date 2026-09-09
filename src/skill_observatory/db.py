from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import NullPool


class Base(DeclarativeBase):
    pass


class SkillRecord(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_key: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    content_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    repo_full_name: Mapped[str] = mapped_column(String(250), index=True)
    repo_url: Mapped[str] = mapped_column(String(500))
    repo_default_branch: Mapped[str] = mapped_column(String(200))
    path: Mapped[str] = mapped_column(String(600))
    name: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(String(200), nullable=True)
    compatibility: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    allowed_tools_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    spec_json: Mapped[dict] = mapped_column(JSON)
    security_json: Mapped[dict] = mapped_column(JSON)
    score_json: Mapped[dict] = mapped_column(JSON)
    resources_json: Mapped[dict] = mapped_column(JSON)
    stars: Mapped[int] = mapped_column(Integer, default=0, index=True)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    pushed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    discovery_source: Mapped[str] = mapped_column(String(100), index=True)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    overall_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    security_score: Mapped[int] = mapped_column(Integer, default=0)
    maintenance_score: Mapped[int] = mapped_column(Integer, default=0)
    adoption_score: Mapped[int] = mapped_column(Integer, default=0)


class RepositorySnapshot(Base):
    __tablename__ = "repository_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo_full_name: Mapped[str] = mapped_column(String(250), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    stars: Mapped[int] = mapped_column(Integer)
    forks: Mapped[int] = mapped_column(Integer)
    open_issues: Mapped[int] = mapped_column(Integer, default=0)
    watchers: Mapped[int] = mapped_column(Integer, default=0)
    score_hint: Mapped[float] = mapped_column(Float, default=0.0)


def make_engine(database_url: str):
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    kwargs = {"poolclass": NullPool} if is_sqlite else {"pool_pre_ping": True}
    return create_engine(database_url, connect_args=connect_args, **kwargs)


def make_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = make_engine(database_url)
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_database(database_url: str) -> None:
    engine = make_engine(database_url)
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session
