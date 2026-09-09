from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class ResourceCounts(BaseModel):
    scripts: int = 0
    references: int = 0
    assets: int = 0
    other: int = 0


class SpecValidation(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ParsedSkill(BaseModel):
    root: Path
    skill_md_path: Path
    name: str
    description: str
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    body: str
    raw: str
    resource_counts: ResourceCounts
    spec: SpecValidation
    files: list[Path] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


Severity = Literal["low", "medium", "high", "critical"]


class SecurityFinding(BaseModel):
    rule: str
    severity: Severity
    file: str
    line: int
    message: str
    evidence: str


class SecurityReport(BaseModel):
    score: int = Field(ge=0, le=100)
    findings: list[SecurityFinding] = Field(default_factory=list)

    @property
    def low(self) -> int:
        return sum(item.severity == "low" for item in self.findings)

    @property
    def medium(self) -> int:
        return sum(item.severity == "medium" for item in self.findings)

    @property
    def high(self) -> int:
        return sum(item.severity == "high" for item in self.findings)

    @property
    def critical(self) -> int:
        return sum(item.severity == "critical" for item in self.findings)


class RepositorySignals(BaseModel):
    stars: int = 0
    forks: int = 0
    pushed_at: datetime
    archived: bool = False
    license_spdx: str | None = None
    has_tests: bool = False
    has_readme: bool = False
    contributors: int = 0
    star_velocity_7d: float = 0.0


class ScoreBreakdown(BaseModel):
    overall: int = Field(ge=0, le=100)
    quality: int = Field(ge=0, le=100)
    security: int = Field(ge=0, le=100)
    maintenance: int = Field(ge=0, le=100)
    adoption: int = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)


class DiscoveredRepository(BaseModel):
    full_name: str
    html_url: str
    default_branch: str = "main"
    description: str = ""
    stars: int = 0
    forks: int = 0
    pushed_at: datetime
    archived: bool = False
    license_spdx: str | None = None
    topics: list[str] = Field(default_factory=list)
    discovery_source: str


class IndexedSkill(BaseModel):
    canonical_key: str
    content_fingerprint: str
    repo_full_name: str
    repo_url: str
    repo_default_branch: str
    path: str
    name: str
    description: str
    license: str | None
    compatibility: str | None
    metadata: dict[str, str]
    allowed_tools: list[str]
    spec: SpecValidation
    security: SecurityReport
    score: ScoreBreakdown
    resources: ResourceCounts
    stars: int
    forks: int
    pushed_at: datetime
    archived: bool
    discovery_source: str
    indexed_at: datetime
    evidence: dict[str, Any] = Field(default_factory=dict)
