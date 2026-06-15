# Sovrn + AdSense 广告集成 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 集成 Sovrn 联盟广告，保留 AdSense，全站加两栏 Grid 布局（侧边栏广告），`ads.txt` 扩展为多网络条目。

**Architecture:** `site_builder/sitemap.py` 的 `generate_ads_txt()` 扩展支持 extra_entries；新增 `_ads.md.j2` 提供 banner/in-content 广告宏；`render_html_page()` 新增 `sidebar_html` 参数，body 改为 CSS Grid 两栏布局；`build_site.py` 传入 sidebar HTML 常量给所有页面。

**Tech Stack:** Python 3.13+, Jinja2, MarkdownIt, pytest

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `site_builder/sitemap.py` | Modify | `generate_ads_txt()` 扩展 extra_entries 参数；新增 `SOVRN_ADS_TXT_ENTRIES` 常量 |
| `content_engine/templates/_ads.md.j2` | **Create** | `ads_banner()` / `ads_incontent()` 两个 Jinja2 宏 |
| `content_engine/templates/_base.md.j2` | Modify | import 广告宏，footer 前插入 in-content 广告 |
| `content_engine/templates/index_screener.md.j2` | Modify | 表格上方加 banner 广告 |
| `content_engine/templates/index_leaderboard.md.j2` | Modify | 表格上方加 banner 广告 |
| `content_engine/templates/ticker_page.md.j2` | Modify | 表格上方加 banner 广告 |
| `site_builder/render.py` | Modify | `sidebar_html` 参数 + Grid CSS + Sovrn 脚本 |
| `build_site.py` | Modify | `ADS_SIDEBAR_HTML` 常量 + 所有 `render_html_page()` 传参 + ads.txt 传 extra_entries |
| `tests/test_sitemap.py` | Modify | 扩展 ads.txt 测试覆盖 Sovrn 条目 |
| `tests/test_render.py` | Modify | 新增 sidebar / layout / Sovrn 脚本测试 |

---

### Task 1: 扩展 `generate_ads_txt()` 支持多网络条目

**Files:**
- Modify: `site_builder/sitemap.py:50-51`
- Modify: `tests/test_sitemap.py:69-73`

- [ ] **Step 1: 在 `site_builder/sitemap.py` 添加 `SOVRN_ADS_TXT_ENTRIES` 常量并修改 `generate_ads_txt()`**

在 `generate_ads_txt` 函数之前插入常量（约 line 49）：

```python
SOVRN_ADS_TXT_ENTRIES = [
    "# SOVRN",
    "lijit.com, 606193, DIRECT, fafdf38b16bf6b2b #SOVRN",
    "lijit.com, 606193-eb, DIRECT, fafdf38b16bf6b2b #SOVRN",
    "openx.com, 538959099, RESELLER, 6a698e2ec38604c6",
    "pubmatic.com, 137711, RESELLER, 5d62403b186f2ace",
    "pubmatic.com, 156212, RESELLER, 5d62403b186f2ace",
    "rubiconproject.com, 17960, RESELLER, 0bfd66d529a55807",
    "appnexus.com, 1019, RESELLER, f5ab79cb980f11d1",
    "video.unrulymedia.com, 2444764291, RESELLER",
    "krushmedia.com, AJxF6R572a9M6CaTvK, RESELLER",
    "motorik.io, 100463, RESELLER",
    "smaato.com, 1100056344, RESELLER, 07bcf65f187117b4",
    "smartadserver.com, 4926, RESELLER, 060d053dcf45cbf3",
    "opera.com, pub10014056052800, RESELLER, 55a0c5fd61378de3",
    "axonix.com, 59143, RESELLER, bc385f2b4a87b721",
    "programmaticx.ai, 100464, RESELLER",
    "sharethrough.com, 4926, RESELLER, d53b998a7bd4ecd2",
]
```

修改 `generate_ads_txt` 函数签名和实现：

```python
def generate_ads_txt(*, publisher_id: str, extra_entries: list[str] | None = None) -> str:
    lines = [f"google.com, {publisher_id}, DIRECT, f08c47fec0942fa0"]
    if extra_entries:
        lines.extend(extra_entries)
    return "\n".join(lines) + "\n"
```

- [ ] **Step 2: 运行现有测试确认向后兼容**

```bash
uv run pytest tests/test_sitemap.py::test_ads_txt_contains_direct_publisher_record -v
```
Expected: PASS（`extra_entries=None` 默认行为不变）

- [ ] **Step 3: 更新 `build_site.py` 调用传入 `extra_entries`**

在 `build_site.py:423`，修改为：

```python
_write(public_dir / "ads.txt", generate_ads_txt(publisher_id=ADSENSE_PUBLISHER_ID, extra_entries=SOVRN_ADS_TXT_ENTRIES))
```

同步更新 import（line 56 不变，`generate_ads_txt` 已 import；新增 `SOVRN_ADS_TXT_ENTRIES`）：

```python
from site_builder.sitemap import (
    SOVRN_ADS_TXT_ENTRIES,
    generate_ads_txt,
    generate_robots_txt,
    generate_sitemap_xml,
)
```

- [ ] **Step 4: 写新测试**

在 `tests/test_sitemap.py` 末尾追加：

```python
def test_ads_txt_includes_sovrn_entries_when_passed():
    from site_builder.sitemap import SOVRN_ADS_TXT_ENTRIES, generate_ads_txt

    txt = generate_ads_txt(
        publisher_id="pub-6718270775160916",
        extra_entries=SOVRN_ADS_TXT_ENTRIES,
    )
    # Google line still first
    assert txt.startswith("google.com, pub-6718270775160916, DIRECT, f08c47fec0942fa0\n")
    # Sovrn comment line present
    assert "# SOVRN" in txt
    # Key Sovrn entries
    assert "lijit.com, 606193, DIRECT, fafdf38b16bf6b2b #SOVRN" in txt
    assert "openx.com, 538959099, RESELLER, 6a698e2ec38604c6" in txt
    assert "pubmatic.com, 137711, RESELLER, 5d62403b186f2ace" in txt
    assert "rubiconproject.com, 17960, RESELLER, 0bfd66d529a55807" in txt
    assert "appnexus.com, 1019, RESELLER, f5ab79cb980f11d1" in txt
    # 18 total lines (1 Google + 1 comment + 16 Sovrn entries)
    assert len(txt.strip().split("\n")) == 18


def test_ads_txt_no_extra_entries_still_works():
    from site_builder.sitemap import generate_ads_txt

    txt = generate_ads_txt(publisher_id="pub-6718270775160916")
    assert txt == "google.com, pub-6718270775160916, DIRECT, f08c47fec0942fa0\n"
```

- [ ] **Step 5: 运行新测试**

```bash
uv run pytest tests/test_sitemap.py -v
```
Expected: 所有 3 个 ads.txt 测试 PASS

- [ ] **Step 6: Commit**

```bash
git add site_builder/sitemap.py build_site.py tests/test_sitemap.py
git commit -m "feat: expand ads.txt generator with Sovrn reseller entries"
```

---

### Task 2: 创建 `_ads.md.j2` 广告宏模板

**Files:**
- Create: `content_engine/templates/_ads.md.j2`

- [ ] **Step 1: 创建模板文件**

```bash
cat > content_engine/templates/_ads.md.j2 << 'J2EOF'
{# Ad unit macros for inline (markdown-flow) placement.
   Sidebar ads are handled separately in build_site.py as raw HTML
   passed to render_html_page(). #}

{% macro ads_banner() %}
<div class="ad-unit ad-banner">
  <ins class="adsbygoogle"
       style="display:block"
       data-ad-client="ca-pub-6718270775160916"
       data-ad-slot="BANNER_SLOT_ID"
       data-ad-format="horizontal"
       data-full-width-responsive="true"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
{% endmacro %}

{% macro ads_incontent() %}
<div class="ad-unit ad-incontent">
  <ins class="adsbygoogle"
       style="display:block;text-align:center"
       data-ad-layout="in-article"
       data-ad-format="fluid"
       data-ad-client="ca-pub-6718270775160916"
       data-ad-slot="INCONTENT_SLOT_ID"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
{% endmacro %}
J2EOF
```

- [ ] **Step 2: 验证 Jinja2 能加载模板**

```bash
uv run python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('content_engine/templates'))
tmpl = env.get_template('_ads.md.j2')
print(tmpl.render())
print('OK: template loads without error')
"
```
Expected: 输出无报错（空渲染结果正常——宏只定义不输出）

- [ ] **Step 3: Commit**

```bash
git add content_engine/templates/_ads.md.j2
git commit -m "feat: add AdSense ad unit macros (banner, in-content)"
```

---

### Task 3: 更新 `render_html_page()` — 两栏 Grid 布局 + Sovrn 脚本

**Files:**
- Modify: `site_builder/render.py`
- Modify: `tests/test_render.py`

- [ ] **Step 1: 添加 `sidebar_html` 参数到 `render_html_page()`**

修改函数签名（line 253 附近），在 `apple_touch_icon_url` 之后加：

```python
def render_html_page(
    *,
    markdown_source: str,
    page_title: str,
    canonical_url: str,
    json_ld_blocks: list[dict],
    description: str | None = None,
    og_image_url: str | None = None,
    theme_color: str | None = None,
    favicon_url: str | None = None,
    apple_touch_icon_url: str | None = None,
    sidebar_html: str = "",
) -> str:
```

- [ ] **Step 2: 在 `<head>` 添加 Sovrn header bidding 脚本**

在 AdSense `<script>` 行之后（line 301 之后），追加：

```python
'<script async src="https://ap.lijit.com/www/delivery/fpi.js?z=606193&width=300&height=250"></script>\n'
```

- [ ] **Step 3: 修改 body 结构为 Grid 布局**

当前 body 输出（line 310-313）：
```python
'<body>\n'
f'{body_html}\n'
'</body>\n'
```

改为：

```python
'<body>\n'
'<div class="page-layout">\n'
'  <main class="main-content">\n'
f'{body_html}\n'
'  </main>\n'
f'  <aside class="sidebar">\n{sidebar_html}  </aside>\n' if sidebar_html else ''
'</div>\n'
'</body>\n'
```

- [ ] **Step 4: 修改 body CSS 规则**

当前 body 规则（line 27-35）：
```css
  body {
    background-color: var(--bg-main);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6;
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
  }
```

移除 `max-width: 960px;`（交给 `.page-layout`）：

```css
  body {
    background-color: var(--bg-main);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 2rem 1.5rem;
  }
```

- [ ] **Step 5: 在 `CSS_STYLE` 末尾（`</style>` 之前）追加 Grid 布局 CSS**

在 `</style>` 之前追加：

```css

  /* ---- Two-column layout ---- */

  .page-layout {
    display: grid;
    grid-template-columns: 1fr 300px;
    gap: 2rem;
    max-width: 1020px;
    margin: 0 auto;
  }

  .main-content {
    min-width: 0;
  }

  .sidebar {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    position: sticky;
    top: 1rem;
    align-self: start;
  }

  .ad-unit {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100px;
  }

  .ad-banner {
    min-height: 90px;
    margin: 0 0 1.5rem;
  }

  .ad-incontent {
    min-height: 100px;
    margin: 2rem 0;
  }

  /* No sidebar: content fills width */
  .page-layout:not(:has(.sidebar)) {
    grid-template-columns: 1fr;
    max-width: 960px;
  }

  /* Mobile: stack */
  @media (max-width: 768px) {
    .page-layout {
      grid-template-columns: 1fr;
      max-width: 960px;
      gap: 1rem;
    }

    .sidebar {
      position: static;
      flex-direction: column;
    }

    .ad-sidebar-300 {
      width: 100%;
      max-width: 336px;
      margin: 0 auto;
    }
  }
```

- [ ] **Step 6: 跑现有 render 测试确认无回归**

```bash
uv run pytest tests/test_render.py -v
```
Expected: 全部 PASS

- [ ] **Step 7: 写新测试**

在 `tests/test_render.py` 末尾追加：

```python
def test_sidebar_html_renders_aside():
    html = render_html_page(
        markdown_source="# Hello",
        page_title="Test",
        canonical_url="https://example.com/",
        json_ld_blocks=[],
        sidebar_html='<div class="ad-unit">AD</div>',
    )
    assert '<aside class="sidebar">' in html
    assert '<div class="ad-unit">AD</div>' in html


def test_no_sidebar_html_omits_aside():
    html = render_html_page(
        markdown_source="# Hello",
        page_title="Test",
        canonical_url="https://example.com/",
        json_ld_blocks=[],
    )
    assert '<aside class="sidebar">' not in html


def test_page_layout_class_present():
    html = render_html_page(
        markdown_source="# Hello",
        page_title="Test",
        canonical_url="https://example.com/",
        json_ld_blocks=[],
    )
    assert 'class="page-layout"' in html
    assert 'class="main-content"' in html


def test_sovrn_script_in_head():
    html = render_html_page(
        markdown_source="# Hello",
        page_title="Test",
        canonical_url="https://example.com/",
        json_ld_blocks=[],
    )
    assert "ap.lijit.com/www/delivery/fpi.js?z=606193" in html


def test_body_max_width_not_set():
    """Grid layout handles max-width; body itself should not have it."""
    html = render_html_page(
        markdown_source="# Hello",
        page_title="Test",
        canonical_url="https://example.com/",
        json_ld_blocks=[],
    )
    # CSS_STYLE is in the output; body rule should NOT contain max-width: 960
    style_start = html.index("<style>")
    style_end = html.index("</style>")
    css = html[style_start:style_end]
    # The body rule should have margin: 0 but no max-width
    assert "max-width" not in css.split("body {")[1].split("}")[0]


def test_grid_css_present():
    html = render_html_page(
        markdown_source="# Hello",
        page_title="Test",
        canonical_url="https://example.com/",
        json_ld_blocks=[],
    )
    assert "grid-template-columns: 1fr 300px" in html
    assert "position: sticky" in html
    assert "@media (max-width: 768px)" in html
```

- [ ] **Step 8: 跑全部 render 测试**

```bash
uv run pytest tests/test_render.py -v
```
Expected: 全部 14 个测试 PASS

- [ ] **Step 9: Commit**

```bash
git add site_builder/render.py tests/test_render.py
git commit -m "feat: add two-column grid layout, Sovrn script, and sidebar_html parameter"
```

---

### Task 4: 更新模板插入广告位

**Files:**
- Modify: `content_engine/templates/_base.md.j2`
- Modify: `content_engine/templates/index_screener.md.j2`
- Modify: `content_engine/templates/index_leaderboard.md.j2`
- Modify: `content_engine/templates/ticker_page.md.j2`

- [ ] **Step 1: 修改 `_base.md.j2` — import 广告宏，插入 in-content 广告**

当前内容：
```jinja2
{# stock/content_engine/templates/_base.md.j2 ... #}
{% block body %}{% endblock %}
{% include "_footer_nav.md.j2" %}
{% include "_disclaimer.md.j2" %}
```

改为：
```jinja2
{# stock/content_engine/templates/_base.md.j2 ... #}
{% from "_ads.md.j2" import ads_banner, ads_incontent with context %}
{% block body %}{% endblock %}
{% include "_footer_nav.md.j2" %}
{{ ads_incontent() }}
{% include "_disclaimer.md.j2" %}
```

- [ ] **Step 2: 修改 `index_screener.md.j2` — Featured Ticker Deep Dives 上方加 banner**

在 `## Featured Ticker Deep Dives`（line 25）之前插入：

```jinja2
{{ ads_banner() }}

## Featured Ticker Deep Dives
```

- [ ] **Step 3: 修改 `index_leaderboard.md.j2` — 同样位置加 banner**

在 `## Featured Ticker Deep Dives`（line 25）之前插入：

```jinja2
{{ ads_banner() }}

## Featured Ticker Deep Dives
```

- [ ] **Step 4: 修改 `ticker_page.md.j2` — Today's Setup 表格上方加 banner**

在 `## Today's Setup`（line 14）之前插入：

```jinja2
{{ ads_banner() }}

## Today's Setup
```

- [ ] **Step 5: 验证模板可以正常渲染**

```bash
uv run python -c "
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('content_engine/templates'))
# Verify _base loads with macros
base = env.get_template('_base.md.j2')
print('_base.md.j2: OK')
# Verify index templates load
screener = env.get_template('index_screener.md.j2')
print('index_screener.md.j2: OK')
leaderboard = env.get_template('index_leaderboard.md.j2')
print('index_leaderboard.md.j2: OK')
ticker = env.get_template('ticker_page.md.j2')
print('ticker_page.md.j2: OK')
"
```
Expected: 四个模板全部 OK

- [ ] **Step 6: Commit**

```bash
git add content_engine/templates/_base.md.j2 content_engine/templates/index_screener.md.j2 content_engine/templates/index_leaderboard.md.j2 content_engine/templates/ticker_page.md.j2
git commit -m "feat: insert ad units (banner + in-content) into page templates"
```

---

### Task 5: 在 `build_site.py` 中传入 sidebar HTML

**Files:**
- Modify: `build_site.py`

- [ ] **Step 1: 添加 `ADS_SIDEBAR_HTML` 常量**

在 `ADSENSE_PUBLISHER_ID`（line 73）之后添加：

```python
ADS_SIDEBAR_HTML = """\
<div class="ad-unit ad-sidebar-300">
  <ins class="adsbygoogle"
       style="display:inline-block;width:300px;height:250px"
       data-ad-client="ca-pub-6718270775160916"
       data-ad-slot="SIDEBAR_SLOT_ID"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
<div class="ad-unit ad-sidebar-300" style="margin-top:1.5rem;">
  <ins class="adsbygoogle"
       style="display:inline-block;width:300px;height:600px"
       data-ad-client="ca-pub-6718270775160916"
       data-ad-slot="SIDEBAR_TALL_SLOT_ID"></ins>
  <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
"""
```

- [ ] **Step 2: 给所有 `render_html_page()` 调用传 `sidebar_html=ADS_SIDEBAR_HTML`**

共 7 处调用，逐个加上参数。位置：

| Line | 页面 | 
|------|------|
| ~137 | `_render_ticker_page()` 正常个股页 |
| ~165 | `_render_ticker_placeholder()` 占位个股页 |
| ~316 | 首页 (index) |
| ~332 | Methodology |
| ~352 | About / Privacy / Contact 循环 |
| ~365 | FAQ |
| ~378 | Guide |

每处 `render_html_page(...)` 调用末尾加 `sidebar_html=ADS_SIDEBAR_HTML`。

示例（首页 line 316-326）：
```python
index_html = render_html_page(
    markdown_source=index_md,
    page_title=index_title,
    canonical_url=f"{base_url}/",
    json_ld_blocks=homepage_blocks,
    description=HOMEPAGE_DESCRIPTION,
    og_image_url=f"{base_url}/og-image.png",
    favicon_url="/favicon.svg",
    apple_touch_icon_url="/apple-touch-icon.png",
    theme_color=THEME_COLOR,
    sidebar_html=ADS_SIDEBAR_HTML,
)
```

- [ ] **Step 3: 构建验证**

```bash
uv run python build_site.py
```
Expected: 构建成功，无报错

- [ ] **Step 4: 检查生成 HTML 的关键特征**

```bash
# sidebar 存在
grep -c 'class="sidebar"' public/index.html
# Expected: 1

# grid layout 存在
grep -c 'class="page-layout"' public/index.html
# Expected: 1

# Sovrn 脚本在 head 中
grep -c 'ap.lijit.com' public/index.html
# Expected: 1

# ads.txt 条目数
wc -l public/ads.txt
# Expected: 18
```

- [ ] **Step 5: 跑全部测试**

```bash
uv run pytest
```
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add build_site.py
git commit -m "feat: pass sidebar ad HTML to all page renders"
```

---

### Task 6: 跑全部测试并构建验证

**Files:** (none new)

- [ ] **Step 1: 跑全部测试**

```bash
uv run pytest -v
```
Expected: 所有测试 PASS，无回归

- [ ] **Step 2: 完整构建**

```bash
uv run python build_site.py
```
Expected: 构建成功

- [ ] **Step 3: 抽查 public/ads.txt**

```bash
head -3 public/ads.txt
wc -l public/ads.txt
```
Expected: 第一行 Google，第二行 `# SOVRN`，第三行 `lijit.com...`；共 18 行

- [ ] **Step 4: 抽查生成的 HTML 页面**

```bash
# 首页有 grid + sidebar
grep -c 'page-layout' public/index.html
grep -c 'main-content' public/index.html
grep -c 'sidebar' public/index.html

# 个股页有 banner + sidebar
grep -c 'ad-banner' public/nvda/index.html
grep -c 'ad-sidebar-300' public/nvda/index.html

# 内容页有 in-content + sidebar
grep -c 'ad-incontent' public/methodology/index.html
```
Expected: 所有计数 >= 1

- [ ] **Step 5: 运行 compliance check（site_builder 内置）**

```bash
uv run python -c "
from build_site import main
# Just verify no import errors; actual build already ran
print('build_site module loads OK')
"
```

- [ ] **Step 6: 最终 Commit（如有遗漏）**

```bash
git status
# 如有遗漏的生成文件或测试输出，提交
```

---

## Self-Review Notes

- Spec §1 (ads.txt 扩展) → Task 1 ✅
- Spec §2 (广告宏) → Task 2 ✅
- Spec §3 (布局/CSS/sidebar_html) → Task 3 ✅
- Spec §4 (Sovrn 脚本) → Task 3 Step 2 ✅
- Spec §5 (模板插入广告) → Task 4 ✅
- Spec §6 (build_site.py 传递 sidebar) → Task 5 ✅
- Spec §7 (测试) → Task 1 Step 4 + Task 3 Step 7 ✅
- 无 TBD / TODO / placeholder
- 所有 `render_html_page()` 调用覆盖 → 7 处全部列出
- BANNER_SLOT_ID / SIDEBAR_SLOT_ID / SIDEBAR_TALL_SLOT_ID / INCONTENT_SLOT_ID 为已知占位符（spec 明确标注需用户替换）
