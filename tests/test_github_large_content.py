from __future__ import annotations

import base64

import httpx

from skill_observatory.github_publisher import GitHubAtomicPublisher

REPOSITORY = "acme/observatory"


def test_read_text_falls_back_to_git_blob_when_contents_is_not_inline_base64() -> None:
    expected = "# Awesome\n" + "entry\n" * 100
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        path = request.url.path
        if path.endswith("/contents/AWESOME.md"):
            return httpx.Response(
                200,
                json={
                    "content": "",
                    "encoding": "none",
                    "sha": "large-blob-sha",
                },
            )
        if path.endswith("/git/blobs/large-blob-sha"):
            encoded = base64.b64encode(expected.encode("utf-8")).decode("ascii")
            return httpx.Response(
                200,
                json={
                    "content": encoded,
                    "encoding": "base64",
                    "sha": "large-blob-sha",
                },
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    publisher = GitHubAtomicPublisher(
        token="token",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )

    actual = publisher._read_text(REPOSITORY, "AWESOME.md", ref="A")

    assert actual == expected
    assert requests == [
        "/repos/acme/observatory/contents/AWESOME.md",
        "/repos/acme/observatory/git/blobs/large-blob-sha",
    ]
