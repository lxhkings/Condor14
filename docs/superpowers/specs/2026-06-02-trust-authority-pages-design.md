# Trust & Authority Pages — AdSense Approval + YMYL E-E-A-T

**日期:** 2026-06-02
**类型:** 可实现 spec（单一实现计划）
**前置:** P1 内容差异化已完成（Track Record + Route C differentiation engine）。
**Spec 路线图归属:** SEO 路线图 P1/收录 + AdSense 变现的共同前置。

---

## 1. 问题

目标：**同时**过两个 Google 关卡。

1. **搜索收录** — 站点是金融内容（YMYL，Your-Money-Your-Life）。Google 质量评审对 YMYL 站要求明确的 About / Contact / 作者主体（E-E-A-T）。当前缺失，放大 thin-content / scaled-content 判定风险。
2. **AdSense 审核** — AdSense `<script>`（`ca-pub-6718270775160916`）已注入每页（`render.py:296`），申请在进行中。AdSense 政策**强制**要求隐私政策页（披露第三方/Google cookie、个性化广告、退出方式）。缺隐私政策 = 必拒。还需可达的联系方式与清晰导航。

当前站点缺口（已确认）：
- 无 `/about/`、`/privacy/`、`/contact/` 页。
- 无站内导航把这些页链起来（仅有 disclaimer 作页脚）。
- 无 `Organization` JSON-LD 主体实体。

## 2. 目标 / 非目标

**目标：**
- 新增 About / Privacy Policy / Contact 三个静态页，进 sitemap、进 IndexNow、被内链。
- 站内页脚导航：每页（含 placeholder 页）链到 Home · Methodology · About · Privacy · Contact。
- 主页发射 `Organization` JSON-LD（含 contactPoint），强化 publisher 实体。
- 全程不触合规红线（禁词扫描仍 exit 0）。

**非目标（YAGNI）：**
- 不改 ticker 页正文 / spintax / 数据管线。
- 不做 cookie consent banner（站点不设自有分析 cookie；Google 广告 cookie 由 AdSense 自身脚本+用户 Google 设置处理，隐私页披露即可。GDPR consent 若日后需要另开子项）。
- 不动 placeholder 页 thin-content + 广告的风险（见 §8 风险，列为后续）。
- 不加 Terms of Service 页（AdSense 不强制；隐私政策才是硬门槛）。

## 3. 架构

沿用现有静态生成器模式：Jinja2 markdown 模板 → `_base.md.j2` 继承链 → `render_html_page()` → `public/<slug>/index.html`。

新增 4 个模板，改 4 个文件，加 1 个测试文件。

### 3.1 新模板（`content_engine/templates/`）

| 模板 | 产出 | 内容要点 |
|------|------|----------|
| `about.md.j2` | `/about/` | 主体=QuantOptions Data Lab；说明这是**自动化的、教育性质的**期权研究项目；数据来源 OPRA via MarketData.app；方法链接 `/methodology/`；重申非投资建议。继承 `_base`。 |
| `privacy.md.j2` | `/privacy/` | **AdSense 关键页。** 披露：第三方厂商（含 Google）使用 cookie 投放基于历史访问的广告；Google 使用广告 cookie；用户可在 Google Ads Settings 退出个性化广告，或经 aboutads.info 退出第三方厂商 cookie；本站不主动收集个人身份信息；问题联系邮箱。继承 `_base`。 |
| `contact.md.j2` | `/contact/` | 主体名 + 可达联系邮箱（`PUBLISHER_EMAIL`）；说明用途（数据/纠错/一般咨询）。继承 `_base`。 |
| `_footer_nav.md.j2` | （被包含） | 一行 markdown 链接导航，包在 `<nav class="sitenav">` 中。 |

`_footer_nav.md.j2` 内容：
```jinja
<nav class="sitenav">

[Home](/) · [Methodology](/methodology/) · [About](/about/) · [Privacy Policy](/privacy/) · [Contact](/contact/)

</nav>
```

### 3.2 `_base.md.j2` 改动

在 body 块后、disclaimer 前插入 footer nav include：
```jinja
{% block body %}{% endblock %}
{% include "_footer_nav.md.j2" %}
{% include "_disclaimer.md.j2" %}
```
所有继承 `_base` 的页（主页两模式、methodology、ticker 页）自动获得页脚导航。

### 3.3 `build_site.py` 改动

- 新增模块常量 `PUBLISHER_EMAIL = "contact@condor14.com"`（见 §8 ACTION）。
- 渲染三个静态页（约在 methodology 渲染之后）→ `public/about/`、`public/privacy/`、`public/contact/`。各页 `json_ld_blocks=[]`（about 页可选挂 Organization，但主页已挂，保持简单 about 页空 blocks）。privacy/contact 模板用 `PUBLISHER_EMAIL` 渲染。
- `_render_ticker_placeholder`：在 `_disclaimer` include 前加 `_footer_nav` include（该函数不走 `_base`）。
- homepage_blocks 追加 `organization_schema(base_url=base_url, contact_email=PUBLISHER_EMAIL)`。
- `static_pages` 列表追加 `("/about/", today)`、`("/privacy/", today)`、`("/contact/", today)`。
- IndexNow `all_urls` 追加这三个 URL。

### 3.4 `content_engine/json_ld.py` 改动

新增：
```python
def organization_schema(*, base_url: str, contact_email: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "QuantOptions Data Lab",
        "url": f"{base_url}/",
        "description": (
            "Automated educational research project tracking 14-day iron "
            "condor setups computed from real OPRA options quotes."
        ),
        "contactPoint": {
            "@type": "ContactPoint",
            "email": contact_email,
            "contactType": "customer support",
        },
    }
```

### 3.5 `render.py` CSS（小幅）

加一条 `.sitenav` 规则（间距 + 字号），与 `.disclaimer` 视觉协调：
```css
.sitenav { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border);
           font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-muted); }
```
链接颜色沿用全局 `a` 规则（绿色）。

## 4. 数据流

无新数据。三页为静态文案，由模板常量/`PUBLISHER_EMAIL` 注入。`Organization` schema 纯静态。无 ledger 依赖。

## 5. 组件边界

- 模板：自含文案，唯一外部依赖是 `PUBLISHER_EMAIL`（privacy/contact）与继承的 `_base`。
- `organization_schema`：纯函数，入参 `base_url` + `contact_email`，出 dict。可独立单测。
- `build_site.py` 编排：唯一改动点是把上述拼进既有 build 流程，不改既有页逻辑。

## 6. 测试（`tests/test_trust_pages.py`）

全部离线，用 `tmp_path` + 既有 `build()` 调用模式（参考 `test_ticker_track_record.py::_build`）。

1. **三页渲染** — build 后 `public/about/index.html`、`privacy/index.html`、`contact/index.html` 存在且非空。
2. **隐私页 AdSense 要件** — privacy HTML 含 `Google`、`cookie`（不区分大小写）、退出链接 `https://www.google.com/settings/ads`（或 `adssettings.google.com`）与 `aboutads.info`，且含 `PUBLISHER_EMAIL`。
3. **联系页** — contact HTML 含 `PUBLISHER_EMAIL`（`mailto:` 链接）。
4. **页脚导航传播** — ticker 页、主页、placeholder 页 HTML 均含 `/privacy/`、`/about/`、`/contact/`、`/methodology/` 链接。
5. **sitemap** — `sitemap.xml` 含 `/about/`、`/privacy/`、`/contact/`。
6. **Organization JSON-LD** — 主页 HTML 含 `"@type":"Organization"` 与 contactPoint email。
7. **合规** — 整次 `build(...)` 返回 0（禁词扫描通过，证明新文案无 "hypothetical" 等禁词）。
8. **json_ld 单测** — `organization_schema(...)` 返回 dict 含正确 `@type`、`url`、`contactPoint.email`。

## 7. 边界 / 合规

- 新文案严禁出现 `hypothetical`（除非进 allowlist，MVP 为空）、`must close`、`guaranteed`、`trading signal`、祈使式推荐。隐私/关于/联系均为中性陈述，天然规避。
- About 页措辞须诚实：明确是**自动化算法**项目，非人工荐股；保持与 disclaimer 一致的 hold-to-expiration / 教育用途口径。
- 隐私政策须真实反映实际：本站除 Google AdSense 脚本外不设自有追踪 cookie；如实陈述。

## 8. 风险 / 待办（ACTION）

- **ACTION（部署前）:** `PUBLISHER_EMAIL = contact@condor14.com` 必须是**可收件**邮箱（域名 catch-all 或转发到真实信箱）才提交 AdSense 审核。AdSense 会核验联系方式可达。若无法配置该邮箱，实现时改为真实可达地址。
- **风险（后续，不在本 spec）:** placeholder ticker 页（"No setup published"）正文极薄却仍挂 AdSense 脚本，AdSense 可能判低价值库存。后续可考虑：placeholder 页不挂广告，或不进 sitemap，或填充更多内容。本轮先不动。
- **风险:** `public/` 当前处于未解决的 merge 冲突（`UU`），但属生成物，一次 `build_site.py` 全量覆盖即解决；实现 Task 末尾 real-build 会顺带清掉。

## 9. 成功判据

- `uv run pytest -q` 全绿（既有 + 新 test_trust_pages）。
- `SITE_HOST=www.condor14.com uv run python build_site.py` exit 0，`public/about|privacy|contact/index.html` 生成，sitemap 含三页。
- 人工抽查：任一页底部可见导航链到 Privacy/About/Contact；隐私页含 Google/cookie/退出说明与联系邮箱。
- （站外，用户执行）AdSense 控制台重新提交审核；GSC 对新页 URL Inspection 请求收录。
