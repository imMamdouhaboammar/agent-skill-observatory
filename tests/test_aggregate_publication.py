import base64
import json
from typing import Any

import httpx

from skill_observatory.aggregate_publication import publish_materialized_views
from skill_observatory.github_publisher import GitHubAtomicPublisher

REPOSITORY = "acme/observatory"
OUTPUTS = {
    "AWESOME.md": "# Catalog\n",
    "data/catalog.json": "[]\n",
    "data/catalog.csv": "canonical_key\n",
    "data/repositories.json": "[]\n",
    "data/stats.json": "{\"skills\": 0}\n",
    "data/refresh.json": "{\"generated_at\": \"new\"}\n",
}


def _content(text: str) -> httpx.Response:
    encoded = base64.b64encode(text.encode()).decode()
    return httpx.Response(200, json={"content": encoded, "encoding": "base64"})


def _json_body(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.content.decode()) if request.content else {}


def test_timestamp_only_change_is_noop() -> None:
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        path = request.url.path
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "A"}})
        if path.endswith("/git/commits/A"):
            return httpx.Response(200, json={"tree": {"sha": "TREE-A"}})
        if "/contents/" in path:
            relative = path.split("/contents/", 1)[1]
            if relative == "data/refresh.json":
                return _content("{\"generated_at\": \"old\"}\n")
            return _content(OUTPUTS[relative])
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubAtomicPublisher(
        token="token", transport=httpx.MockTransport(handler), sleep=lambda _: None
    )
    result = publish_materialized_views(
        publisher, OUTPUTS, repository=REPOSITORY, branch="main"
    )

    assert result.status == "noop"
    assert not any(method == "POST" for method, _ in requests)
    assert not any(method == "PATCH" for method, _ in requests)


def test_meaningful_aggregate_change_creates_one_fast_forward_commit() -> None:
    requests: list[tuple[str, str, dict[str, Any]]] = []
    blob_number = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal blob_number
        body = _json_body(request)
        requests.append((request.method, request.url.path, body))
        path = request.url.path
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "A"}})
        if path.endswith("/git/commits/A"):
            return httpx.Response(200, json={"tree": {"sha": "TREE-A"}})
        if "/contents/" in path:
            relative = path.split("/contents/", 1)[1]
            if relative == "AWESOME.md":
                return _content("# Old catalog\n")
            return _content(OUTPUTS[relative])
        if path.endswith("/git/blobs"):
            blob_number += 1
            return httpx.Response(201, json={"sha": f"blob-{blob_number}"})
        if path.endswith("/git/trees"):
            assert body["base_tree"] == "TREE-A"
            paths = {entry["path"] for entry in body["tree"]}
            assert paths <= set(OUTPUTS)
            assert "AWESOME.md" in paths
            assert "data/refresh.json" in paths
            return httpx.Response(201, json={"sha": "TREE-C"})
        if path.endswith("/git/commits"):
            assert body["message"] == "catalog: refresh materialized views"
            assert body["parents"] == ["A"]
            return httpx.Response(201, json={"sha": "C"})
        if path.endswith("/git/refs/heads/main"):
            assert body == {"sha": "C", "force": False}
            return httpx.Response(200, json={"object": {"sha": "C"}})
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubAtomicPublisher(
        token="token", transport=httpx.MockTransport(handler), sleep=lambda _: None
    )
    result = publish_materialized_views(
        publisher, OUTPUTS, repository=REPOSITORY, branch="main"
    )

    assert result.status == "published"
    assert result.commit_sha == "C"
    assert result.parent_sha == "A"
    assert sum(path.endswith("/git/commits") for _, path, _ in requests) == 1


def test_rejects_non_aggregate_paths_before_network_access() -> None:
    publisher = GitHubAtomicPublisher(
        token="token",
        transport=httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(AssertionError("network called"))
        ),
        sleep=lambda _: None,
    )

    try:
        publish_materialized_views(
            publisher,
            {**OUTPUTS, "README.md": "not allowed"},
            repository=REPOSITORY,
        )
    except ValueError as exc:
        assert "aggregate path" in str(exc)
    else:
        raise AssertionError("expected aggregate path validation failure")
