from __future__ import annotations

import base64
import time
from collections.abc import Callable
from datetime import UTC
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from .directory import DirectoryPatch, render_skill_event
from .events import PublicationResult, PublishedSkillRecord, SkillEvent
from .publication_store import skill_record_path


class GitHubPublisherError(RuntimeError):
    pass


class GitHubPublisherTransportError(GitHubPublisherError):
    pass


class GitHubPublicationConflict(GitHubPublisherError):
    pass


class GitHubAtomicPublisher:
    def __init__(
        self,
        *,
        token: str,
        api_url: str = "https://api.github.com",
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not token:
            raise GitHubPublisherError("GitHub token is required for atomic publication")
        self._sleep = sleep
        self._client = httpx.Client(
            base_url=api_url.rstrip("/"),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "agent-skill-observatory/atomic-publisher",
            },
            timeout=timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> dict[str, Any] | None:
        try:
            response = self._client.request(method, path, params=params, json=json_body)
        except httpx.RequestError as exc:
            raise GitHubPublisherTransportError(f"GitHub transport failure: {exc}") from exc
        if allow_not_found and response.status_code == 404:
            return None
        if response.is_error:
            detail = response.text[:500]
            raise GitHubPublisherError(
                f"GitHub {method} {path} failed with {response.status_code}: {detail}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise GitHubPublisherError(f"GitHub {method} {path} returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise GitHubPublisherError(f"GitHub {method} {path} returned non-object JSON")
        return payload

    def _get(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        allow_not_found: bool = False,
    ) -> dict[str, Any] | None:
        return self._request(
            "GET", path, params=params, allow_not_found=allow_not_found
        )

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = self._request("POST", path, json_body=body)
        if payload is None:
            raise GitHubPublisherError(f"GitHub POST {path} returned no payload")
        return payload

    def _patch_ref(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.patch(path, json=body)
        except httpx.RequestError as exc:
            raise GitHubPublisherTransportError(f"GitHub ref update transport failure: {exc}") from exc
        if response.status_code in {409, 422}:
            raise GitHubPublicationConflict(
                f"GitHub rejected non-fast-forward ref update with {response.status_code}"
            )
        if response.is_error:
            raise GitHubPublisherError(
                f"GitHub PATCH {path} failed with {response.status_code}: {response.text[:500]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise GitHubPublisherError(f"GitHub PATCH {path} returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise GitHubPublisherError(f"GitHub PATCH {path} returned non-object JSON")
        return payload

    @staticmethod
    def _required_str(payload: dict[str, Any], *keys: str) -> str:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                raise GitHubPublisherError(f"GitHub response missing {'.'.join(keys)}")
            current = current[key]
        if not isinstance(current, str) or not current:
            raise GitHubPublisherError(f"GitHub response has invalid {'.'.join(keys)}")
        return current

    def current_head(self, repository: str, branch: str = "main") -> str:
        payload = self._get(f"/repos/{repository}/git/ref/heads/{quote(branch, safe='')}")
        if payload is None:
            raise GitHubPublisherError("GitHub branch ref unexpectedly missing")
        return self._required_str(payload, "object", "sha")

    def _commit_tree(self, repository: str, commit_sha: str) -> str:
        payload = self._get(f"/repos/{repository}/git/commits/{commit_sha}")
        if payload is None:
            raise GitHubPublisherError("GitHub commit unexpectedly missing")
        return self._required_str(payload, "tree", "sha")

    def _read_text(
        self,
        repository: str,
        path: str,
        *,
        ref: str,
        allow_missing: bool = False,
    ) -> str | None:
        encoded_path = quote(path, safe="/")
        payload = self._get(
            f"/repos/{repository}/contents/{encoded_path}",
            params={"ref": ref},
            allow_not_found=allow_missing,
        )
        if payload is None:
            return None
        content = payload.get("content")
        encoding = payload.get("encoding")
        if not isinstance(content, str) or encoding != "base64":
            raise GitHubPublisherError(f"GitHub content payload invalid for {path}")
        try:
            return base64.b64decode(content, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise GitHubPublisherError(f"GitHub content is not valid UTF-8 base64 for {path}") from exc

    def _read_canonical_record(
        self, repository: str, event: SkillEvent, *, ref: str
    ) -> PublishedSkillRecord | None:
        text = self._read_text(
            repository,
            str(skill_record_path(event.canonical_key)),
            ref=ref,
            allow_missing=True,
        )
        if text is None:
            return None
        try:
            record = PublishedSkillRecord.model_validate_json(text)
        except (ValidationError, ValueError) as exc:
            raise GitHubPublisherError(
                f"corrupted canonical published record for {event.canonical_key}"
            ) from exc
        if record.canonical_key != event.canonical_key:
            raise GitHubPublisherError(
                f"canonical record path mismatch for {event.canonical_key}"
            )
        return record

    @staticmethod
    def _already_applied(
        event: SkillEvent, current: PublishedSkillRecord | None
    ) -> bool:
        if event.type == "remove":
            return current is None
        if current is None or event.after is None:
            return False
        return (
            current.source_fingerprint == event.after.source_fingerprint
            and current.analysis_fingerprint == event.after.analysis_fingerprint
        )

    @staticmethod
    def _commit_subject(event: SkillEvent) -> str:
        record = event.after or event.before
        if record is None:
            raise GitHubPublisherError("Skill event has no state for commit subject")
        return f"skill({event.type}): {record.skill.name} · {record.skill.repo_full_name}"

    @staticmethod
    def _commit_message(event: SkillEvent) -> str:
        record = event.after or event.before
        if record is None:
            raise GitHubPublisherError("Skill event has no state for commit metadata")
        skill = record.skill
        raw_categories = (skill.evidence or {}).get("categories") or []
        categories = sorted({str(item).strip() for item in raw_categories if str(item).strip()})
        observed_at = event.observed_at
        if observed_at.tzinfo is not None:
            observed_at = observed_at.astimezone(UTC)
        source = record.source_fingerprint or "none"
        analysis = record.analysis_fingerprint or "none"
        return "\n".join(
            [
                GitHubAtomicPublisher._commit_subject(event),
                "",
                f"Skill-Key: {event.canonical_key}",
                f"Event: {event.type}",
                f"Source-Fingerprint: {source}",
                f"Analysis-Fingerprint: {analysis}",
                f"Overall-Score: {skill.score.overall}",
                f"Security-Score: {skill.security.score}",
                f"Categories: {', '.join(categories) if categories else 'none'}",
                f"Observed-At: {observed_at.isoformat()}",
            ]
        )

    def _create_blobs(
        self, repository: str, patch: DirectoryPatch
    ) -> dict[str, str]:
        shas: dict[str, str] = {}
        for path in sorted(patch.writes):
            encoded = base64.b64encode(patch.writes[path].encode("utf-8")).decode("ascii")
            payload = self._post(
                f"/repos/{repository}/git/blobs",
                {"content": encoded, "encoding": "base64"},
            )
            shas[path] = self._required_str(payload, "sha")
        return shas

    def _create_tree(
        self,
        repository: str,
        *,
        base_tree: str,
        patch: DirectoryPatch,
        blob_shas: dict[str, str],
    ) -> str:
        entries: list[dict[str, Any]] = []
        for path in sorted(patch.writes):
            entries.append(
                {
                    "path": path,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_shas[path],
                }
            )
        for path in sorted(patch.deletes):
            entries.append(
                {"path": path, "mode": "100644", "type": "blob", "sha": None}
            )
        payload = self._post(
            f"/repos/{repository}/git/trees",
            {"base_tree": base_tree, "tree": entries},
        )
        return self._required_str(payload, "sha")

    def _create_commit(
        self,
        repository: str,
        *,
        tree_sha: str,
        parent_sha: str,
        event: SkillEvent,
    ) -> str:
        payload = self._post(
            f"/repos/{repository}/git/commits",
            {
                "message": self._commit_message(event),
                "tree": tree_sha,
                "parents": [parent_sha],
            },
        )
        return self._required_str(payload, "sha")

    def publish_event(
        self,
        event: SkillEvent,
        catalog_after_event: dict[str, PublishedSkillRecord],
        *,
        repository: str,
        branch: str = "main",
        max_attempts: int = 5,
    ) -> PublicationResult:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        for attempt in range(1, max_attempts + 1):
            try:
                head_sha = self.current_head(repository, branch)
                tree_sha = self._commit_tree(repository, head_sha)
                readme = self._read_text(repository, "README.md", ref=head_sha)
                if readme is None:
                    raise GitHubPublisherError("root README.md is missing")
                current = self._read_canonical_record(repository, event, ref=head_sha)
                if self._already_applied(event, current):
                    return PublicationResult(
                        canonical_key=event.canonical_key,
                        event_type=event.type,
                        status="noop",
                        parent_sha=head_sha,
                        attempts=attempt,
                    )

                patch = render_skill_event(
                    event,
                    catalog_after_event,
                    current_root_readme=readme,
                )
                blob_shas = self._create_blobs(repository, patch)
                new_tree_sha = self._create_tree(
                    repository,
                    base_tree=tree_sha,
                    patch=patch,
                    blob_shas=blob_shas,
                )
                commit_sha = self._create_commit(
                    repository,
                    tree_sha=new_tree_sha,
                    parent_sha=head_sha,
                    event=event,
                )
                self._patch_ref(
                    f"/repos/{repository}/git/refs/heads/{quote(branch, safe='')}",
                    {"sha": commit_sha, "force": False},
                )
                return PublicationResult(
                    canonical_key=event.canonical_key,
                    event_type=event.type,
                    status="published",
                    commit_sha=commit_sha,
                    parent_sha=head_sha,
                    attempts=attempt,
                    files_changed=sorted([*patch.writes, *patch.deletes]),
                )
            except GitHubPublicationConflict:
                if attempt >= max_attempts:
                    return PublicationResult(
                        canonical_key=event.canonical_key,
                        event_type=event.type,
                        status="deferred",
                        attempts=attempt,
                    )
                self._sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))
            except GitHubPublisherTransportError:
                if attempt >= max_attempts:
                    raise
                self._sleep(min(0.1 * (2 ** (attempt - 1)), 1.0))

        raise AssertionError("unreachable publication retry state")
