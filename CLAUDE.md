# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
uv sync                              # 安装依赖
uv run pytest                        # 运行所有测试
uv run pytest tests/test_xxx.py -v                    # 运行单个测试文件
uv run pytest tests/test_xxx.py::test_foo -v          # 运行单个测试
MARKETDATA_API_KEY=xxx uv run python daily_run.py     # 手动执行数据管线
SITE_HOST=example.com uv run python build_site.py     # 手动构建静态站点
```

## 架构总览

**管线**: `daily_run.py`（数据）→ `build_site.py`（静态站点），由 GitHub Actions 串联执行（工作日 22:00 UTC）。

### Plan A — 数据管线

**data_source/**（网络 I/O）→ **math_engine/**（纯函数）→ **ledger/**（状态持久化），由 `daily_run.py` 编排。

- `data_source/marketdata.py` — `MarketDataClient` 封装 MarketData.app REST API（quote / option_chain / daily_bars）；测试通过 `httpx` transport injection mock。
- `data_source/cache.py` — `DailyBarsCache`：SQLite 缓存日线 bar，upsert 语义。
- `data_source/trading_calendar.py` — 基于 `pandas-market-calendars` NYSE 日历的交易日判断。
- `math_engine/` — 全是纯函数：`atr.py`（Wilder ATR14）、`sma.py`（SMA20 + 趋势偏向分类，0.5% band）、`strike_picker.py`（spot ± 1.5×ATR14 锚定行权价）、`iron_condor.py`（4 腿 condor 构建 + 行权价顺序校验）、`expiration.py`（13–16 天窗口内最近到期日）、`liquidity.py`（bid>0, spread/mid≤0.30, OI≥100）、`pnl_evaluator.py`（持有至到期结算：won/lost + P&L）。
- `ledger/schema.py` — `Setup`（25 字段 frozen dataclass）、`Settlement`、`DailyMark`、`Ledger`（可变容器，含 `setups`、`skipped`、`site_launch_date`、`first_settlement_date`）。
- `ledger/store.py` — `LedgerStore`：原子写入（tmp + fsync + os.replace），文件缺失时返回空 Ledger。
- `ledger/stats.py` — 30 日滚动统计：胜率、最大回撤（peak-to-trough）、单笔最大亏损、累计 P&L；`per_ticker_stats()` 按 ticker 分组。
- `daily_run.py` — 交易日守卫 → 结算已到期 setup → 为每个 ticker 开新仓 → 原子持久化。`list_expirations()` wrapper 支持测试 monkeypatch。
- `config.py` — 20 ticker 列表 + 5 个行业的 `SECTORS` 映射（Semiconductors / Mega-Cap Tech / Software / Index ETFs / Intl & High-Beta，每个行业至少 2 个 ticker）。

### Plan B — 静态站点生成器

**content_engine/**（内容生成）→ **site_builder/**（HTML/SEO/合规）→ `build_site.py`（编排）→ `public/`（静态产出）。

- `content_engine/silo.py` — `same_sector_peers(ticker, n=4)`：同行业内部链接，字母序排列，确定性输出。
- `content_engine/json_ld.py` — 三个 JSON-LD schema 发射器：`FinancialProduct`（用 `additionalProperty[]`，禁用 `offers.price`）、`BreadcrumbList`（Home → Sector → Ticker）、`Article`（作者=QuantOptions Data Lab）。
- `content_engine/spintax.py` — 按 `(trend_bias, iv_percentile, vol_regime)` 选择 9 模板之一，注入 vol_regime 修饰句后渲染。IV 分桶：>70=high, <30=low。Vol regime：ATR14/ATR60 >1.2=expanding, <0.8=contracting。
- `content_engine/tracking_log.py` — `build_tracking_log()`：12 周滚动周五行，已结算 setup 映射至结算周周五，进行中 setup 每周 emit 一行。
- `content_engine/templates/` — Jinja2/Markdown 模板：`_base.md.j2`（基础布局 + 免责声明继承链）、`ticker_page.md.j2`、`index_screener.md.j2`（Mode A，切换前）、`index_leaderboard.md.j2`（Mode B，切换后）、`methodology.md.j2`、`spintax/`（9 个散文模板 + `_modifier.md.j2`）。
- `site_builder/render.py` — `render_html_page()`：markdown-it-py（commonmark + table）→ HTML5 完整页面，JSON-LD 块用紧凑格式注入 `<head>`。
- `site_builder/screener.py` — Mode A 首页数据：top 10 权利金 setup（按 credit/max_loss 降序）、行业波动率热力图、当日新开 setup。
- `site_builder/leaderboard.py` — `cutover_satisfied()`：settled≥200 且距首次结算≥30 天时切换 Mode B。`build_leaderboard_data()`：按 ticker 聚合 30 日胜率，按 win_rate → setups_tracked → ticker 排序。
- `site_builder/sitemap.py` — sitemap.xml（ticker 页 daily 0.8、静态页 weekly 0.5）+ robots.txt。
- `site_builder/indexnow.py` — 向 Bing/Yandex 发送 IndexNow ping（非 Google）；key 文件持久化（`data/indexnow_key.txt`），不可重新生成；`diff_changed_urls()` 用 `data/last_indexed.json` 追踪变更。
- `site_builder/compliance.py` — 构建时对 `*.html` 执行 "hypothetical" 词扫描；仅允许 `HYPOTHETICAL_ALLOWLIST` 中的精确句子（MVP 为空）。存在违规时 `build_site.py` exit 2。
- `build_site.py` — 构建编排器：加载 ledger → 切换判断 → 渲染首页 → methodology → 20 ticker 页（无 setup 时降级为占位页）→ sitemap → robots.txt → IndexNow key → ping → 合规检查。入口：`main()` 从 ET 时区取 `today`，从 `SITE_HOST` 环境变量取域名。
- `vercel.json` — `framework: null`、`outputDirectory: "public"`、`trailingSlash: true`、`ignoreCommand`：`chore(data):` 提交通过 grep exit 0 跳过构建。

**首页切换机制**：开站时显示 Mode A（筛选器），一旦 settled≥200 且距首次结算≥30 天，自动切换 Mode B（领跑榜）。此切换由 `cutover_satisfied()` 实现。

### 合规红线

- 所有用户可见文案中**禁止**出现 "hypothetical" 一词，除非精确匹配 `HYPOTHETICAL_ALLOWLIST`（MVP 中为空）。
- 免责声明文字为规范原文（`_disclaimer.md.j2`），结构性/格式性修改（如分段、HTML 包裹）是允许的，但法律实质内容不可更改。
- 禁止使用的语言："must close"、"guaranteed"、"trading signal"、祈使式推荐。

## 测试

- 网络相关测试使用 `httpx.MockTransport`，mock 数据在 `tests/fixtures/marketdata/`。
- 管线级测试通过 monkeypatch `MarketDataClient` / `list_expirations` 隔离网络调用。
- `LedgerStore` 文件测试使用 `tmp_path` fixture。
- 所有测试均可离线运行，无需真实 API key。
- Plan A 模板不变性测试（`test_spintax.py`）：模板间句子重叠率 ≤30%，`vol_regime_modifier` 标记精确出现一次，注入后无断句错误。

## 部署

- **Vercel**：导入 `lxhkings/Condor14`，Framework=Other，Output Directory=`public`。`vercel.json` 控制忽略规则和 trailing slash。
- **GitHub Actions**：`daily_run.yml` 交易日 22:00 UTC 运行；`mirror_math_engine.yml` 在 `math_engine/**` 变更时 subtree split 到 `lxhkings/iron-condor-math-engine`。
- **必需 secret**：`MARKETDATA_API_KEY`（MarketData.app）、`MIRROR_DEPLOY_KEY`（SSH 私钥，用于推送数学引擎镜像）。
