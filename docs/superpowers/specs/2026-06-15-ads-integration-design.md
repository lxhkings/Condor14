# Sovrn + AdSense 广告集成 — Design Spec

**Date:** 2026-06-15
**Status:** Draft
**Goal:** 集成 Sovrn 联盟广告 + 保留 AdSense，全站加侧边栏广告位。

## 前置状态

- `public/ads.txt` 已有 Google 一行（由 `site_builder/sitemap.py:generate_ads_txt()` 生成）
- `<head>` 已加载 AdSense 脚本（`site_builder/render.py:301`）
- 当前单栏布局，`body` max-width 960px
- AdSense 内容质量改进已完成（2026-06-14 spec）

## 变更概览

| # | 变更 | 文件 |
|---|------|------|
| 1 | ads.txt 生成扩展为多网络列表 | `site_builder/sitemap.py` |
| 2 | 新增广告宏模板 | `content_engine/templates/_ads.md.j2` (新增) |
| 3 | 布局改为两栏 Grid（桌面端） | `site_builder/render.py` |
| 4 | `<head>` 加 Sovrn header bidding 脚本 | `site_builder/render.py` |
| 5 | `_base.md.j2` 插入 banner + in-content 广告位 | `content_engine/templates/_base.md.j2` |
| 6 | `build_site.py` 传递 sidebar 广告 HTML | `build_site.py` |
| 7 | 测试 | `tests/` |

## 1. ads.txt 生成扩展

**文件:** `site_builder/sitemap.py`

将 `generate_ads_txt(*, publisher_id: str) -> str` 改为 `generate_ads_txt(*, publisher_id: str, extra_entries: list[str] | None = None) -> str`。

Google 条目始终在第一行，其后追加 Sovrn 条目。

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

`build_site.py` 调用处更新为传入 `extra_entries=SOVRN_ADS_TXT_ENTRIES`。

## 2. 广告宏模板（新增）

**文件:** `content_engine/templates/_ads.md.j2`

两个宏（banner + in-content），在 markdown 模板里调用，输出原始 HTML（MarkdownIt 配置了 `html: True`，不会转义）。Sidebar 广告不走模板宏——由 `build_site.py` 直接构建 HTML 字符串传给 `render_html_page()`。

```jinja2
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
```

> **注意:** `BANNER_SLOT_ID` / `INCONTENT_SLOT_ID` 是占位符，需在 AdSense 后台创建广告单元后替换。

## 3. 布局改动

**文件:** `site_builder/render.py`

### 3a. render_html_page() 新增参数

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
    sidebar_html: str = "",  # NEW
) -> str:
```

### 3b. body 结构改为 Grid

```html
<body>
<div class="page-layout">
  <main class="main-content">
    {body_html}
  </main>
  <aside class="sidebar">
    {sidebar_html}
  </aside>
</div>
</body>
```

保持向下兼容：若 `sidebar_html` 为空，不渲染 `<aside>`，`<main>` 占满全宽。

### 3c. CSS 新增 Grid 布局

在 `CSS_STYLE` 末尾追加：

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
  min-width: 0; /* prevent grid blowout */
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

同时调整 `body` 规则：移除 `max-width: 960px`（交给 `.page-layout` 控制），保留底色和字体。

## 4. `<head>` 加 Sovrn 脚本

**文件:** `site_builder/render.py`

在 AdSense 脚本之后追加：

```html
<script async src="https://ap.lijit.com/www/delivery/fpi.js?z=606193&width=300&height=250"></script>
```

## 5. `_base.md.j2` 插入广告位

**文件:** `content_engine/templates/_base.md.j2`

```jinja2
{% from "_ads.md.j2" import ads_banner, ads_incontent with context %}
{% block body %}{% endblock %}
{% include "_footer_nav.md.j2" %}
{{ ads_incontent() }}
{% include "_disclaimer.md.j2" %}
```

首页和个股页模板（`index_screener.md.j2`、`index_leaderboard.md.j2`、`ticker_page.md.j2`）在表格上方调用 `{{ ads_banner() }}`：

```jinja2
{% from "_ads.md.j2" import ads_banner with context %}
{{ ads_banner() }}
## Today's Setups
...
```

## 6. `build_site.py` 传递 sidebar

**文件:** `build_site.py`

sidebar HTML 在 `build_site.py` 顶部作为常量定义，传给所有 `render_html_page()` 调用（slot ID 是常量，无需模板渲染）：

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

每个 `render_html_page()` 调用传入 `sidebar_html=ADS_SIDEBAR_HTML`。

## 7. 测试

| 测试 | 验证点 |
|------|--------|
| `test_ads_txt.py` | ads.txt 包含 Google + 全部 17 行 Sovrn 条目 |
| `test_ads_layout.py` | 桌面端 `.page-layout` 两栏 grid；移动端单栏 |
| `test_ads_units.py` | render_html_page() 含 sidebar_html 时渲染 `<aside>`；不含时不渲染 |
| 现有测试 | 全部通过，无回归 |

## 广告位分布总结

| 页面 | Banner | Sidebar 300×250 | Sidebar 300×600 | In-Content |
|------|--------|-----------------|-----------------|------------|
| 首页 (screener/leaderboard) | 表格上方 | ✅ | ✅ | — |
| 个股页 | 表格上方 | ✅ | ✅ | — |
| Methodology | — | ✅ | ✅ | 段落间 |
| FAQ | — | ✅ | ✅ | 段落间 |
| Guide | — | ✅ | ✅ | 段落间 |
| About / Contact / Privacy | — | ✅ | ✅ | — |

## 不干的事

- 不碰 `daily_run.py`
- 不碰 `math_engine/`、`data_source/`、`ledger/`
- 不改现有表格、卡片、文字样式的任何 CSS 规则
- 不删 `public/ads.txt` 的现有 Google 条目

## Verification

1. `uv run pytest` — 所有测试通过，包含新增测试
2. `uv run python build_site.py` — 构建成功，`public/ads.txt` 含 18 行（1 Google + 1 注释 + 16 Sovrn）
3. 浏览器检查：桌面端两栏布局，侧边栏 sticky；移动端单栏
4. `curl https://condor14.com/ads.txt` 返回完整列表
