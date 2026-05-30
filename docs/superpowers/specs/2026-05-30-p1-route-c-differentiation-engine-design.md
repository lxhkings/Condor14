# P1 路线C — 激活内容差异化引擎

**日期:** 2026-05-30
**类型:** 实现 spec（可走 plan→实现）
**父文档:** [SEO 路线图](2026-05-29-seo-roadmap-design.md) P1；承接 [P1 路线A Track Record](2026-05-30-p1-content-differentiation-design.md)
**路线:** C（让模板化散文真正分化）

---

## 1. 背景与诊断

P1 路线A 已把真实 per-ticker 数据搬上页面（Track Record / Settlement / Active 表，每 ticker 数字唯一）。但**顶部 3 段散文**（页面 above-fold）仍是 thin-content：

**审计实证（2026-05-30，渲染产物比对）:**
- AAPL 与 TSLA 顶部 3 段散文**逐字相同**，仅注入数字不同。
- 18 个活跃 ticker 全部显示 `50th percentile` IV，全部无波动率修饰句。

**根因（两个差异化轴全瘫痪）:**

| 轴 | 现状 | 根因 |
|----|------|------|
| IV 分位桶 | 恒 `medium` → 9 个 spintax 模板只用 3 个（`*_medium`），`*_low`/`*_high` 死代码 | `daily_run.py:176` `iv_percentile_at_open=50` 硬编码占位 |
| vol_regime 修饰句 | 恒 `stable` → 修饰句恒空串 | `build_site.py:87` 误传 `atr60=setup.atr14_at_open`，ratio 恒 1.0；真实 atr60 从未计算/存储 |

结果：18 页按 `trend_bias` 塌缩成 ~3 种 intro 变体，同 bias ticker 顶部段雷同。

**附带问题:** 给用户展示的 `50th percentile` 是假数据 —— 既削 SEO 又轻微违 honesty。

---

## 2. 目标

激活两个差异化轴，用**真实数据**驱动，使 9 个 spintax 模板全部可达、同 bias ticker 不再共享逐字散文；并把 per-ticker 战绩注入散文。

**成功判据:**
- 9 个 `{bias}_{bucket}` 模板按真实分位可达（低/中/高波动 ticker 落不同桶）
- atr14 与 atr60 背离的 ticker，vol_regime 修饰句非空
- 散文不再出现 `Implied volatility`，改为 `Realized volatility`，分位数为真实计算值
- 有结算史的 ticker，散文含一句战绩引用（措辞异于 Track Record 块）
- 同 bias 两 ticker（如 AAPL/TSLA）顶部段不再逐字相同
- 测试全绿；合规扫描无新禁词

---

## 3. 范围

**做（分 3 阶段，见 §7）:**
- C-1 真波动率（HV）分位，替换 IV=50 stub
- C-2 schema 字段改名 `iv_percentile_at_open` → `vol_percentile_at_open`（诚实）
- C-3 真 atr60 → 激活 vol_regime 修饰句
- C-4 散文文案 `Implied volatility` → `Realized volatility`
- C-5 散文注入 Track Record 一句
- C-6（按需，重测后才决定）扩 spintax 模板池

**不做:**
- 扩页 / 新 ticker（P2）
- 内链 silo（P3）
- 期权 IV 历史落地（路线 B，已否决：填充空窗期长、攒库复杂）

---

## 4. 数据来源策略（已定：方案 A）

`percentile` 数字来源 = **实现波动率（Historical/Realized Volatility）分位**，从 `data_source/cache.py` 的 OHLCV bar 算，排 52 周分布。

**否决项:**
- 方案 B（逐日落地 ATM IV 攒 IV-rank）：需新存储 + 数月填充空窗，近期无法分桶。
- 方案 C（HV 分位但仍写 "IV"）：假数据，正是本 spec 要修的问题。

**诚实约束:** HV 是后向已实现量；散文措辞必须为 `Realized volatility`，不得写 `Implied`。schema 字段亦改名以消除 "iv" 误导。

---

## 5. 改动明细

### C-1 真波动率分位 — `math_engine/volatility.py`（新）+ `daily_run.py`

新模块两函数（纯函数，无 I/O）：

```python
def realized_vol(closes: Sequence[float], window: int = 20) -> float:
    """年化已实现波动率 = 最近 window 日对数收益的样本标准差 × sqrt(252)。
    需 >= window+1 个 close。"""

def vol_percentile(closes: Sequence[float], window: int = 20, lookback: int = 252) -> int:
    """对 trailing lookback 个交易日的滚动 realized_vol 序列，
    计算最新值的百分位 rank，返回 0–100 int。
    历史不足（< window + MIN_RANK_SAMPLE）→ 返回 50（显式占位，记日志）。"""
```

- `MIN_RANK_SAMPLE`（如 30）：rank 样本下限，不足则退 50（= 当前 medium 行为，优雅降级）。
- `daily_run.py:176`：`iv_percentile_at_open=50` → `vol_percentile_at_open=vol_percentile(closes)`。
- `_refresh_bars`（daily_run.py:71）：抓取窗 `today - 60d` → `today - 400d`（≈272 交易日，满足 lookback=252 + window）；`cache.read` 窗同步放宽。cache 为 SQLite，存量无上限压力。
- Futu `daily_bars` 单 ticker 单次调用，400 日历日无 rate-limit 压力。

### C-2 schema 改名 — `ledger/schema.py` + `content_engine/spintax.py`

- `Setup.iv_percentile_at_open: int` → `vol_percentile_at_open: int`。
- `from_dict`（schema.py:145 区域）：
  `vol_percentile_at_open = d.get("vol_percentile_at_open", d.get("iv_percentile_at_open", 50))`（旧 ledger 兼容）。
- `to_dict`：只写新键。
- `spintax.py`：`classify_iv_percentile` → `classify_vol_percentile`（逻辑不变：>70 high，<30 low，else medium）；`render_prelude` 读 `setup.vol_percentile_at_open`，模板变量名同步。

### C-3 真 atr60 → 激活 regime — `math_engine/atr.py` + `schema.py` + `daily_run.py` + `build_site.py`

- `atr.py`：加 `atr60(bars)`（或泛化 `atr(bars, period)`），需 >= period+1 bar。
- `schema.py`：`Setup` 加 `atr60_at_open: float`。`from_dict` 默认
  `d.get("atr60_at_open", d["atr14_at_open"])` → 旧 setup ratio=1.0 → stable（保持当前行为，graceful）。`to_dict` 写新字段。
- `daily_run.py`：抓取窗放宽后 bar 足够，计算 `atr60_value`，存入 Setup。
- `build_site.py:87`：`atr60=setup.atr14_at_open` → `atr60=setup.atr60_at_open`。

### C-4 散文文案修正 — `content_engine/templates/spintax/*.md.j2`（9 文件）

- `Implied volatility registers at the {{ iv_percentile_at_open }}th percentile`
  → `Realized volatility registers at the {{ vol_percentile_at_open }}th percentile`。
- 9 个模板（bullish/bearish/neutral × low/medium/high）均含此句，逐一改。
- 合规：`realized volatility` 为描述性术语，无 allowlist 外禁词。

### C-5 散文注入 Track Record — `spintax.py` + 新 partial

- `render_prelude` 加可选参 `track_record: dict | None`。
- `build_site.py`：传 `track_record=alltime_stats.get(ticker)`（路线A 已算出 `alltime_stats`）。
- 新 partial `content_engine/templates/spintax/_track_record_line.md.j2`：单句、`sample_size > 0` 守卫、措辞**异于** Track Record 块的叙事句。示例方向：
  > `{{ ticker }}'s {{ track_record.sample_size }} prior settled cycles provide an empirical reference point for the strikes framed today.`
- 9 个 bias 模板末尾 `{% include 'spintax/_track_record_line.md.j2' %}`（共享 partial，避免 9 处重复逻辑）。
- `track_record is None` 或 `sample_size == 0` → partial 不输出。

### C-6 扩模板池（按需，Phase 3 重测后才做）

- 每桶加 1–2 phrasing 变体，`render_prelude` 按 `zlib.crc32(ticker.encode()) % N` 选变体（确定性、ticker 稳定）。
- 实现可选：模板内 `{% if variant == 0 %}...{% elif %}` 或独立 `{bias}_{bucket}_{v}.md.j2` 文件。
- **触发条件:** Phase 3 重跑重复审计，若同桶仍高 verbatim 重叠才做。预期 C-1（9 桶分散）+ C-5（每 ticker 唯一数字句）已打破雷同，C-6 大概率不必。

---

## 6. 数据流

```
daily_run.main()
  └─ _refresh_bars(window 400d)  → closes(~272)
  └─ atr14(closes15+) ; atr60(closes61+) ; sma20
  └─ vol_percentile(closes, lookback=252) → int
  └─ Setup(vol_percentile_at_open=…, atr60_at_open=…)
       → ledger.json

build_site.main()
  └─ alltime_stats = per_ticker_alltime_stats(led)   # 路线A 已有
  └─ render_prelude(setup, atr60=setup.atr60_at_open,
                    track_record=alltime_stats.get(ticker))
       └─ classify_vol_percentile → 桶 ∈ {low,medium,high}
       └─ classify_vol_regime(atr14, atr60) → 修饰句
       └─ spintax/{bias}_{bucket}.md.j2 + _track_record_line 渲染
```

---

## 7. 分阶段执行（关键：先验证再加码）

| Phase | 含 | 验证 |
|-------|-----|------|
| **1 解锁引擎** | C-1 + C-2 + C-3 + C-4 | 9 桶可达；regime 句随 ticker 变；散文无 `Implied`，分位为真实值 |
| **2 注唯一性** | C-5 | 同 bias 两 ticker（AAPL/TSLA）顶部段不再逐字相同 |
| **3 重测→按需** | 重跑重复审计 → 仅高重叠才做 C-6 | 同桶 verbatim 重叠率 |

---

## 8. 测试

- `tests/test_volatility.py`（新）：
  1. `realized_vol` 已知序列结果正确
  2. `vol_percentile` 单调性 —— 高波动尾部序列 → 高分位；低波动 → 低分位
  3. 历史不足（< window+MIN_RANK_SAMPLE）→ 返回 50
- `tests/test_atr.py`：加 `atr60` 用例（含 bar 不足报错）
- schema round-trip：
  1. 旧 ledger（含 `iv_percentile_at_open`、无 `atr60_at_open`）反序列化 → `vol_percentile_at_open` 取旧值、`atr60_at_open` 默认 = atr14
  2. 新 Setup 序列化→反序列化幂等
- spintax：
  1. 分位 <30 / 30–70 / >70 → 选 `*_low` / `*_medium` / `*_high`
  2. atr14 与 atr60 背离（ratio>1.2 / <0.8）→ 修饰句非空；相等 → 空
  3. `track_record.sample_size>0` → 含战绩句；`None` / 0 → 不含
  4. 文案断言 `Realized volatility`，否定 `Implied volatility`
- compliance（`site_builder/compliance.py`）构建时照旧执行，CI 把关禁词
- build_site 端到端渲染通过

---

## 9. 边界与风险

| 情况 | 行为 |
|------|------|
| 新 ticker 历史 < ~250 bar | `vol_percentile` 退 50（medium）；`atr60` 不足时退默认 → regime stable。= 当前行为，优雅降级 |
| Futu 抓 400 日历日 | 单 ticker 单次调用，无 rate-limit 压力 |
| 旧已结算 setup 存的 50 / atr14 默认 | 仅最新 setup 驱动顶部散文，旧值不影响展示 |
| HV vs IV 语义 | HV = 已实现（后向）；文案必须 `Realized`，比 `Implied` 前瞻 claim 更可辩护 |
| C-6 工作量 | 9× 新合规散文为最重项；置于 Phase 3 按需，避免投机性写作 |

---

## 10. 合规

- `Realized volatility` 描述性、无 allowlist 外禁词。
- Track Record 注入句陈述过往事实（过去结算周期数），无前瞻承诺、无 `guaranteed`/`must close`/`trading signal`/祈使句。
- 免责声明继承链（`_disclaimer.md.j2`）已覆盖页面，含 past-performance 声明。
