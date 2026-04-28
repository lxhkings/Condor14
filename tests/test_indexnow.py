# tests/test_indexnow.py
import json
from pathlib import Path

import httpx
import pytest

from site_builder.indexnow import diff_changed_urls, ping_indexnow, read_key


def test_read_key_returns_stripped_hex(tmp_path):
    f = tmp_path / "k.txt"
    f.write_text("abcdef0123456789  \n")
    assert read_key(f) == "abcdef0123456789"


def test_read_key_raises_on_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_key(tmp_path / "nope.txt")


def test_diff_changed_urls_first_run_returns_all(tmp_path):
    state = tmp_path / "last.json"
    out = diff_changed_urls(
        current_urls=["https://x/a", "https://x/b"],
        last_indexed_path=state,
    )
    assert sorted(out) == ["https://x/a", "https://x/b"]
    saved = json.loads(state.read_text())
    assert sorted(saved) == ["https://x/a", "https://x/b"]


def test_diff_changed_urls_subsequent_run_returns_only_new(tmp_path):
    state = tmp_path / "last.json"
    state.write_text(json.dumps(["https://x/a"]))
    out = diff_changed_urls(
        current_urls=["https://x/a", "https://x/b"],
        last_indexed_path=state,
    )
    assert out == ["https://x/b"]
    assert sorted(json.loads(state.read_text())) == ["https://x/a", "https://x/b"]


def test_ping_indexnow_posts_correct_payload():
    captured = {}
    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"status": "ok"})
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    ping_indexnow(
        key="abcd1234",
        host="example.com",
        urls=["https://example.com/nvda/", "https://example.com/tsla/"],
        client=client,
    )
    assert "indexnow" in captured["url"]
    assert captured["body"]["host"] == "example.com"
    assert captured["body"]["key"] == "abcd1234"
    assert captured["body"]["keyLocation"] == "https://example.com/abcd1234.txt"
    assert sorted(captured["body"]["urlList"]) == [
        "https://example.com/nvda/", "https://example.com/tsla/",
    ]


def test_ping_indexnow_swallows_http_errors():
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    client = httpx.Client(transport=transport)
    # Must NOT raise; IndexNow is fire-and-forget.
    ping_indexnow(key="x", host="example.com", urls=["https://example.com/"], client=client)


def test_ping_indexnow_skips_when_url_list_empty():
    called = []
    def handler(request: httpx.Request) -> httpx.Response:
        called.append(request)
        return httpx.Response(200, json={})
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    ping_indexnow(key="x", host="example.com", urls=[], client=client)
    assert called == []
