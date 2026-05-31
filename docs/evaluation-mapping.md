# AI Review Cockpit — 评审指标映射

本文档将项目的实现映射到标准评审维度。每个章节列出已交付的内容及其代码位置。

---

## 1. 产品设计（UI/UX）

| 指标 | 实现 | 位置 |
|------|------|------|
| 首页 | 产品导向的着陆页，包含 Hero、功能卡片、流水线预览 | `templates/index.html`、`main.py:37-39` |
| 任务进度 | 实时轮询进度条，包含阶段清单和文件风险条 | `templates/task_progress.html` |
| 报告驾驶舱 | 四个指标卡片、文件风险地图、流水线条、评审决策卡片 | `templates/report.html` |
| 证据链 | 每个发现的结构化证据轨迹，展示来源→置信度链条 | `templates/report.html`（发现卡片） |
| 规则页面 | 静态规则参考页，每条规则包含代码示例（好/坏） | `templates/rules.html`、`main.py:80-97` |
| 任务历史 | 分页任务列表，支持搜索、状态过滤、操作链接 | `templates/task_history.html`、`main.py:42-75` |
| 响应式布局 | Bootstrap 5 栅格系统，包含侧边栏、卡片、交互式过滤 | 所有模板继承 `templates/base.html` |
| shadcn/ui 原型 | 独立的 React + Tailwind + shadcn/ui 仪表盘，展示未来迁移路径 | `frontend-prototype/` |

---

## 2. 功能

| 指标 | 实现 | 位置 |
|------|------|------|
| PR 输入 | GitHub PR 地址解析与验证 | `app/github_client.py:parse_pr_url()` |
| Diff 获取 | GitHub API 集成，获取 PR diff、元数据、变更文件 | `app/github_client.py` |
| 15 条静态规则 | 确定性的仅 patch 扫描（S001–S015） | `app/static_scanner.py` |
| 变更行分析 | 解析 unified diff，仅提取新增/修改行 | `app/diff_utils.py:parse_patch()` |
| 文件风险评分 | 按路径模式、变更大小、内容关键词评分 | `app/risk_scorer.py` |
| AI 文件审查 | 基于 LLM 的逐文件分析，支持深度/普通/跳过路由 | `app/ai_client.py` |
| AI 跨文件分析 | 跨文件一致性检查（需要 ≥2 个变更文件） | `app/review_engine.py:_cross_file_analysis()` |
| PR 摘要生成 | LLM 生成一行摘要、模块变更、业务影响 | `app/ai_client.py:summarize_pr()` |
| 签名去重 | 按文件 + 类型 + 行号桶 + 标题去重 | `app/review_engine.py:_merge_findings()` |
| 置信度评分 | 基础分 + 证据分 + 同意加成 − 不确定性扣减 | `app/confidence_calculator.py` |
| GitHub 评论 | 将高置信度发现发布到 PR，支持幂等更新 | `app/report_generator.py:generate_github_comment()` |
| 反馈系统 | 标记发现为有效 / 误报 / 已解决 | `app/routers/reports.py:submit_feedback()` |
| REST API | 10 个端点，覆盖任务 CRUD、报告、文件、反馈、系统状态、评测 | `app/routers/` |

---

## 3. 交互性

| 指标 | 实现 | 位置 |
|------|------|------|
| 实时进度 | 任务进度页每 2 秒自动轮询 | `templates/task_progress.html`（JavaScript） |
| 文件风险地图 | 可视化风险条，点击可过滤发现 | `templates/report.html`（JavaScript） |
| 严重等级标签页 | 按 critical/high/medium/low 过滤发现 | `templates/report.html`（JavaScript） |
| 置信度过滤 | 开关隐藏低置信度发现（< 0.60） | `templates/report.html`（JavaScript） |
| 键盘快捷键 | 1–5 切换过滤、F 下一条、R 刷新 | `templates/report.html`（JavaScript） |
| 反馈按钮 | 内联有效/误报/已解决，通过 POST 反馈 API | `templates/report.html`、`app/routers/reports.py` |
| 搜索与过滤 | 按地址搜索任务历史，按状态过滤 | `templates/task_history.html`、`main.py:42-75` |
| 分页 | 历史视图每页 20 条任务 | `main.py:52-56` |

---

## 4. 创新

| 创新点 | 说明 | 位置 |
|--------|------|------|
| 变更行审查 | 仅分析 unified diff 中的新增行——零遗留代码噪音 | `app/diff_utils.py` |
| 风险感知路由 | 文件评分（-2 到 15）决定分析深度（深度/普通/跳过） | `app/risk_scorer.py` |
| 混合规则 + AI | 15 条静态规则 + LLM 分析，重叠时给予同意加成 | `app/review_engine.py`、`app/static_scanner.py`、`app/ai_client.py` |
| 置信度门禁 | 三层阈值：≥0.80 GitHub、0.60–0.79 报告、<0.60 隐藏 | `app/confidence_calculator.py` |
| 证据链 | 每个发现的结构化 JSON，展示来源→置信度轨迹 | `app/review_engine.py`、`templates/report.html` |
| 评审决策驾驶舱 | 报告设计为合并决策辅助工具，而非仅仅发现列表 | `templates/report.html`、`main.py:158-169` |
| 签名去重 | 多维度去重（文件 + 类型 + 行号桶 + 标题） | `app/review_engine.py:_merge_findings()` |

---

## 5. 架构

| 指标 | 实现 | 位置 |
|------|------|------|
| 框架 | FastAPI，自动 OpenAPI 文档 | `main.py` |
| 数据库 | SQLAlchemy + SQLite，4 个模型 | `app/database.py`、`app/models.py` |
| 7 阶段流水线 | FETCHING_PR → BUILDING_CONTEXT → STATIC_SCAN → AI_PR_SUMMARY → AI_FILE_REVIEW → AI_CROSS_FILE → MERGING_RESULTS | `app/review_engine.py:run_review()` |
| 模块化设计 | 16+ 个模块，各司其职（scanner、scorer、confidence、diff、context、rule_catalog、golden_evaluation、system_status、ai_provider 等） | `app/` |
| 路由分离 | API 路由与页面路由分离 | `app/routers/`（API）、`main.py`（页面） |
| 配置管理 | 基于环境变量的配置，支持 `.env` | `config.py` |
| 模板继承 | 基础布局被所有页面继承 | `templates/base.html` |

---

## 6. 代码质量

| 指标 | 实现 | 位置 |
|------|------|------|
| 测试覆盖 | 15 个文件共 86 个测试 | `tests/` |
| 测试范围 | Diff 解析、静态规则、风险评分、置信度计算、URL 解析、页面渲染、报告生成、编排引擎、系统状态、数据库迁移、AI 客户端、Provider 适配、评测框架、任务状态、配置兼容 | `tests/test_diff_utils.py`、`tests/test_static_scanner.py`、`tests/test_risk_scorer.py`、`tests/test_confidence_calculator.py`、`tests/test_github_client.py` 等 15 个文件 |
| CI | GitHub Actions：lint、test、import-check，Python 3.10 | `.github/workflows/ci.yml` |
| 类型提示 | 所有函数和数据类完整类型注解 | 所有 `app/` 模块 |
| 错误处理 | API 错误使用 HTTPException，流水线故障使用任务状态 | `app/review_engine.py`、`app/routers/` |
| 数据一致性 | 严重等级按 rank 排序（非字符串），置信度感知过滤，兜底默认值 | `main.py:126-134`、`app/routers/reports.py:30-33` |

---

## 7. PR 流程

| PR | 分支 | 说明 |
|----|------|------|
| #1 | `docs/architecture` | 架构图、测试文档、CI 徽章 |
| #2 | `ci/add-github-actions` | GitHub Actions CI 工作流（lint、test、Python 3.10） |
| #3 | `test/add-core-tests` | 5 个核心模块共 28 个单元测试 |
| #4 | `fix/report-data-consistency` | 文件 ID 绑定、严重等级排序、报告字段对齐 |
| #5 | `demo/high-risk-pr` | 高风险 PR 场景的演示数据 |
| #6 | `feat/task-history` | 分页任务历史列表，支持搜索和状态过滤 |
| #7 | `feat/github-comment-idempotent` | GitHub 评论幂等更新 |
| #8 | `feat/report-ui-optimization` | 报告页面交互优化 |
| #9 | `feat/rules-explanation` | 静态规则说明页面（S001–S015） |
| #10 | `feat/review-cockpit-home` | 产品着陆页，驾驶舱品牌 |
| #11 | `feat/report-cockpit-dashboard` | 驾驶舱仪表盘，风险地图和流水线可视化 |
| #12 | `feat/evidence-chain` | 可解释性发现的结构化证据链 |
| #13 | `prototype/shadcn-review-dashboard` | React + shadcn/ui 前端原型 |
| #14 | `feat/real-cockpit-metrics` | 数据库中真实流水线指标持久化 |
| #15 | `feat/demo-documentation` | 端到端操作指南和 README 创新总结 |
| #16 | `fix/cockpit-data-consistency` | 排序顺序、品牌命名、README 准确性修复 |
| — | `docs/final-demo-walkthrough` | 最终评审文档、评审指标映射、README 亮点 |

**模式：** 每个 PR 聚焦单一关注点（feat/fix/docs/test/ci/prototype）。分支生命周期短，通过标准 PR 流程合并。

---

## 8. 总结

| 维度 | 评分依据 |
|------|---------|
| 产品设计 | 6 个 UI 页面（首页、进度、报告、规则、历史、基础模板），一致的驾驶舱品牌 |
| 功能完整性 | 从 PR 输入到 GitHub 评论的完整 7 阶段流水线，15 条规则 + AI |
| 交互性 | 实时轮询、键盘快捷键、点击过滤、反馈系统 |
| 创新性 | 变更行审查、风险感知路由、混合规则+AI、置信度门禁、证据链 |
| 架构 | 16+ 个模块、4 个数据库模型、10 个 API 端点、FastAPI + SQLAlchemy |
| 代码质量 | 86 个测试通过、类型提示、CI、全链路错误处理 |
| PR 流程 | 18+ 个 PR，范围清晰，增量交付 |
