# P1 内容差异化 — per-ticker Track Record 段

**日期:** 2026-05-30
**类型:** 实现 spec（可走 plan→实现）
**父文档:** [SEO 路线图](2026-05-29-seo-roadmap-design.md) P1
**路线:** A（把已有真实数据搬上页面）

---

## 1. 目标

逆转 Google thin-content / scaled-content-abuse 判定：让每个 ticker 页含**真实唯一**内容——基于已结算 setup 的 per-ticker 战绩。数据已存在（`ledger.stats.per_ticker_alltime_stats`），无需新算法。

**成功判据:**
- 每个有结算记录的 ticker 页出现 `## Track Record` 段，数值正确
- 段末叙事句每 ticker 数字不同（唯一文本）
- methodology 重复 boilerplate 删除
- 测试全绿；合规扫描无新禁词

---

## 2. 范围

**做:**
- ticker 页加独立 `## Track Record (All-Time Settled)` 段
- methodology 摘要去重（删 3 条重复 bullet，留链接）

**不做（本轮）:**
- 散文注入统计（留给后续路线 C）
- 扩页 / 新 ticker（P2）
- 内链 silo（P3）

---

## 3. 数据来源

`ledger/stats.py::per_ticker_alltime_stats(ledger) -> dict[ticker, dict]`，已存在。每 ticker 返回：

| 字段 | 含义 |
|------|------|
| `sample_size` | 已结算 setup 数 |
| `win_rate` | 胜率 0–1（0 结算时 None） |
| `cumulative_pnl` | 累计 P&L/spread（可负） |
| `worst_single_loss` | 最差单笔（无亏损时 0.0） |
| `max_drawdown` | 峰谷回撤（≤0） |

负 P&L 如实展示（已确认接受）。

---

## 4. 改动（3 文件）

### 4.1 `build_site.py`
- `main()` 加载 ledger 后调用一次 `per_ticker_alltime_stats(led)`，得 `alltime_stats` dict
- 沿调用链传入 `_render_ticker`（新增参数 `track_record: dict | None`）
- `_render_ticker` 把本 ticker 的 stats（`alltime_stats.get(setup.ticker)`）传给模板变量 `track_record`
- 一次计算，避免每页重复调用全量统计

### 4.2 `content_engine/templates/ticker_page.md.j2`
- 在 `## Risk Profile` 与 `## Methodology Snapshot` 之间插入：

```jinja
{% if track_record and track_record.sample_size > 0 %}
## Track Record (All-Time Settled)

| Metric | Value |
| :--- | ---: |
| Settled setups | {{ track_record.sample_size }} |
| Win rate | {{ "%.0f"|format(track_record.win_rate * 100) }}% |
| Cumulative P&L | ${{ "%.2f"|format(track_record.cumulative_pnl) }} |
| Worst single loss | ${{ "%.2f"|format(track_record.worst_single_loss) }} |
| Max drawdown | ${{ "%.2f"|format(track_record.max_drawdown) }} |

Across {{ track_record.sample_size }} settled 14-day Iron Condor setups on
{{ ticker }}, the structure resolved inside the short strikes
{{ "%.0f"|format(track_record.win_rate * 100) }}% of the time, for a
cumulative realized result of ${{ "%.2f"|format(track_record.cumulative_pnl) }}
per spread.
{% endif %}
```

- `sample_size == 0` 或 `track_record is None` → 整段不渲染

### 4.3 methodology 去重
- 删除 `ticker_page.md.j2` 中 `## Methodology Snapshot` 下 3 条重复 bullet（strike selection / pricing / win condition）
- **保留** `[Full methodology →](/methodology/)` 链接（改为段内单行）

---

## 5. 合规

- Track Record = 已结算真实历史，描述性过往表现
- 不含 "hypothetical"（allowlist 外禁词）、"guaranteed"、"must close"、"trading signal"、祈使句
- 叙事句用过去式陈述事实（"resolved inside the short strikes X% of the time"），无前瞻承诺
- 免责声明继承链（`_disclaimer.md.j2`）已覆盖页面

---

## 6. 测试

新增 `tests/test_ticker_track_record.py`（或并入现有 build/site 测试）：

1. **有战绩渲染** — 构造 ledger 含某 ticker 多个已结算 setup，断言渲染含 `## Track Record`、正确 sample_size / win% / cumPnL 字符串
2. **零战绩隐藏** — ticker 无结算（sample_size=0）→ 渲染不含 `## Track Record`
3. **track_record=None** — 段不渲染，页仍有效
4. **叙事句唯一性** — 两个不同 ticker（不同 win_rate）→ 叙事句文本不同
5. **负 P&L 渲染** — cumulative_pnl<0 正确显示负号
6. **methodology 去重** — 渲染不含已删 bullet 文本，仍含 methodology 链接

合规扫描（`site_builder/compliance.py`）构建时照旧执行，CI 把关禁词。

---

## 7. 边界

| 情况 | 行为 |
|------|------|
| ticker 从未结算 | 无 Track Record 段，页有效 |
| `win_rate=None`（0 结算） | 被 `sample_size>0` 守卫，不触及格式化 |
| 全胜 ticker | `worst_single_loss=0.0`、`max_drawdown=0.0` 正常显示 |
| placeholder 页（无开仓） | 不受影响（`_render_ticker_placeholder` 不变） |

---

## 8. 数据流

```
main()
  └─ load ledger
  └─ alltime_stats = per_ticker_alltime_stats(led)   # 一次
  └─ for ticker: _render_ticker(..., track_record=alltime_stats.get(ticker))
       └─ ticker_page.md.j2 渲染 Track Record 段（条件）
```
