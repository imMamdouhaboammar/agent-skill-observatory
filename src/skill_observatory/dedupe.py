from __future__ import annotations

import hashlib
import re


def canonical_skill_key(owner: str, repo: str, path: str) -> str:
    normalized_path = re.sub(r"/+", "/", path.strip("/ ").lower())
    return f"{owner.strip().lower()}/{repo.strip().lower()}:{normalized_path}"


def content_fingerprint(content: str) -> str:
    normalized = "\n".join(line.rstrip() for line in content.replace("\r\n", "\n").split("\n")).strip() + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
