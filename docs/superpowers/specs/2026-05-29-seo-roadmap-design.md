# SEO 路线图 — Condor14 programmatic SEO

**日期:** 2026-05-29
**类型:** 策略分解文档（decomposition doc，非可直接实现的 spec）
**目标:** 长尾流量规模 —— 成百上千长尾词，每词少量流量

---

## 1. 现状（2026-05-29 Semrush + GSC）

| 指标 | 值 | 解读 |
|------|-----|------|
| 建站年龄 | ~1 个月（2026-04-28 起） | 沙盒期，crawl budget 极低 |
| Authority Score | 0 | 无站外权重 |
| Backlinks / Ref domains | 9 / 6 | 接近零 |
| Organic Keywords | 2 | 几乎未进 index |
| Organic Traffic | 0 | —— |
| GSC sitemap | 18/19 报 "Redirect" 错误 | **已修**（canonical→www，commit bb3728e） |
| Position Tracking | "iron condor screener" 未上榜 | 目标词无排名 |

**站点架构:** programmatic SEO。18 个 ticker 页 + 首页 + methodology，工作日自动生成。每页 = 同构数据表 + 1/9 spintax 散文 + methodology 摘要 + 内链。

---

## 2. 核心矛盾（必须正视）

> **programmatic scale + 模板化内容 = Google "scaled content abuse" 政策的精确打击对象。**

2024 年 3 月 Google spam update 明确针对"为操纵排名而批量生成的低价值页面"。本站 18 页同构、9 模板轮换，正落在判定区。

**含义:** 单纯"扩页规模"在内容差异化解决前会放大风险，不是放大收益。所以 **内容差异化是过收录关的前提，必须排第一**。

**合规红线（不可破）:** 禁止 "hypothetical" 词（除非 allowlist）；禁止 "must close"/"guaranteed"/"trading signal"/祈使式推荐；免责声明法律实质不可改。所有 SEO 内容改造受此约束。

---

## 3. 四杠杆 × 优先级（目标=长尾规模）

| 优先级 | 杠杆 | 性质 | 我能做 | 状态 |
|--------|------|------|--------|------|
| **P0** | 收录修复 | 代码✓ + 手动 | redirect 已修；GSC 重提交要你点 | 半完成 |
| **P1** | 内容差异化 | 纯代码 | 全做 | 待 brainstorm |
| **P2** | 扩页规模 | 纯代码 | 全做 | 待 brainstorm |
| **P3** | 内部链接 / silo | 纯代码 | 全做 | 待 brainstorm |
| **P4** | Backlinks | 站外营销 | 仅出策略 | 不进代码闭环 |

**顺序逻辑:** P1 不解决，P2 扩页 = 放大 spam 风险；P3 silo 在页变多后才有意义；P4 是慢变量，前期次要。

---

## 4. 子项分解（每个独立走 spec→plan→实现）

### P0 — 收录修复（剩手动步骤，无需 spec）
1. 等 Vercel 部署完，`curl https://www.condor14.com/sitemap.xml` 确认 200 无跳转
2. GSC → Sitemaps，对 `www.condor14.com/sitemap.xml` 重新提交
3. URL Inspection 手动请求收录几个核心页
4. 数日后看 Pages 报告，确认 "Redirect" 错误消失

### P1 — 内容差异化（**下一个 brainstorm 目标，最大杠杆**）
让每个 ticker 页有真实独特价值，逆转 thin-content 判定。候选方向（brainstorm 时细化）：
- 每页注入 per-ticker 独特数据/历史/统计文本（已有 daily_marks、settlement、stats 可用）
- 减少 9 模板间结构重叠，扩充模板池或参数化生成
- 利用已落地的 settlement history、win-rate 等真实数据作为差异化内容
- methodology 摘要去重（当前 18 页完全相同）

### P2 — 扩页规模
- 加 ticker（config.TICKERS 现 18）
- 新页型（sector 页 / 对比页 / 历史归档页？）
- 注意：必须在 P1 达标后做，否则放大风险

### P3 — 内部链接 / silo
- 现有 `content_engine/silo.py` same_sector_peers
- 页变多后强化 silo 结构、面包屑、hub 页

### P4 — Backlinks（营销，非代码）
- 出策略文档：目标站点类型、outreach 角度、可发布的数据资产（如 win-rate 排行可作为"可引用数据"吸引自然链接）

---

## 5. 本轮终点

写完本路线图 → 用户审阅 → **brainstorm P1（内容差异化）** 作为第一个子项目，走完整 spec→plan→实现。P0 手动步骤并行由用户执行。

---

## 6. 成功判据

- **P0:** GSC "Redirect" 错误归零，18+ 页进入 "Indexed" 或 "Crawled"
- **P1:** 页间内容重叠率显著下降；GSC "Crawled - currently not indexed" 比例下降
- **整体（3–6 月）:** Organic Keywords 从 2 → 数十+；长尾词开始进 Top 100
