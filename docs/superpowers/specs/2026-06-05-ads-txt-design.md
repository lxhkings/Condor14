# ads.txt Generator — Design

**Date:** 2026-06-05
**Status:** Approved

## Problem

Google AdSense reports the site's `ads.txt` status as **未找到 (not found)**: the last
crawl of `condor14.com` found no `ads.txt` file. Without it, AdSense cannot confirm the
publisher is authorized to sell inventory on the domain, which limits ad serving.

The site already loads the AdSense script with publisher ID `ca-pub-6718270775160916`
(`site_builder/render.py:301`), but no `public/ads.txt` exists.

## Goal

Serve `https://www.condor14.com/ads.txt` containing the authorized publisher record so
AdSense's crawler flips the status from 未找到 → 已授权 (authorized).

Required file content (single line):

```
google.com, pub-6718270775160916, DIRECT, f08c47fec0942fa0
```

- `google.com` — ad system domain.
- `pub-6718270775160916` — the publisher ID (the existing `ca-pub-...` value without the
  `ca-` prefix).
- `DIRECT` — direct seller relationship.
- `f08c47fec0942fa0` — Google's fixed certification authority ID (identical for every
  AdSense publisher).

## Approach

Generate the file during the static-site build, mirroring the existing `robots.txt`
generator. Chosen over a hand-committed static file so the publisher ID lives in one place
with the rest of the site config and the output is covered by tests.

### Changes

| Item | Detail |
|---|---|
| New function | `generate_ads_txt(*, publisher_id: str) -> str` in `site_builder/sitemap.py` (already home to `generate_robots_txt`). |
| Output | `f"google.com, {publisher_id}, DIRECT, f08c47fec0942fa0\n"` |
| Publisher ID source | Constant in `build_site.py` (e.g. `ADSENSE_PUBLISHER_ID = "pub-6718270775160916"`), passed to the generator. |
| Write step | In `build_site.py`, after the `robots.txt` write (~`build_site.py:351`): `_write(public_dir / "ads.txt", generate_ads_txt(publisher_id=ADSENSE_PUBLISHER_ID))`. |
| Immediate deploy | Also hand-write `public/ads.txt` (committed) so the file ships on the next deploy without waiting for the cron build. |
| Test | New test asserting format: contains `google.com`, the correct `pub-` ID, `DIRECT`, and certification ID `f08c47fec0942fa0`. |

### Why `sitemap.py`

It already owns root-level `.txt` generators (`generate_robots_txt`). Same responsibility,
no new file needed.

## Data flow

```
build_site.py (ADSENSE_PUBLISHER_ID)
  → generate_ads_txt()
  → public/ads.txt
  → Vercel deploy
  → AdSense crawler → status 已授权
```

## Out of scope

- No change to the AdSense script tag (already present).
- No multi-publisher / reseller (`RESELLER`) lines — single direct publisher only.

## Verification

1. `uv run pytest` — new ads.txt test passes.
2. `uv run python build_site.py` — `public/ads.txt` generated with exact expected content.
3. After deploy, `curl https://www.condor14.com/ads.txt` returns the record; AdSense
   re-crawl flips status to 已授权.
