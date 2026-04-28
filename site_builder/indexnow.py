# stock/site_builder/indexnow.py
"""IndexNow ping for Bing/Yandex (NOT Google -- Google does not accept the API
for non-JobPosting / non-LiveStream content).

The verification key file at {host}/{key}.txt must be reachable and contain
exactly the key string. The key MUST persist across runs -- if it's regenerated,
all prior pings get rejected.
"""

import json
import logging
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"


def read_key(key_path: Path) -> str:
    return key_path.read_text().strip()


def diff_changed_urls(
    *,
    current_urls: list[str],
    last_indexed_path: Path,
) -> list[str]:
    if last_indexed_path.exists():
        try:
            last = set(json.loads(last_indexed_path.read_text()))
        except json.JSONDecodeError:
            last = set()
    else:
        last = set()
    current = set(current_urls)
    new = sorted(current - last)
    last_indexed_path.parent.mkdir(parents=True, exist_ok=True)
    last_indexed_path.write_text(json.dumps(sorted(current)))
    return new


def ping_indexnow(
    *,
    key: str,
    host: str,
    urls: list[str],
    client: httpx.Client | None = None,
) -> None:
    if not urls:
        log.info("indexnow: no urls to ping, skipping")
        return
    payload = {
        "host": host,
        "key": key,
        "keyLocation": f"https://{host}/{key}.txt",
        "urlList": urls,
    }
    own_client = client is None
    if client is None:
        client = httpx.Client(timeout=10.0)
    try:
        try:
            resp = client.post(INDEXNOW_ENDPOINT, json=payload)
            log.info("indexnow ping: status=%s urls=%d", resp.status_code, len(urls))
        except httpx.RequestError as e:
            log.warning("indexnow ping failed: %s", e)
    finally:
        if own_client:
            client.close()
