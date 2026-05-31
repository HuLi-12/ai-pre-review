# AI Review Cockpit 使用文档

本文档说明如何在本地启动项目、提交 GitHub PR 审查任务、查看审查报告，以及使用 Golden Evaluation 展示系统相对普通 diff-to-LLM 审查的质量控制能力。

## 1. 环境准备

### Python 后端

```bash
pip install -r requirements.txt
```

可选环境变量：

```bash
GITHUB_TOKEN=ghp_xxx
AI_PROVIDER=auto
AI_API_KEY=sk_xxx
AI_API_BASE=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
AI_DEEP_MODEL=gpt-4o
AI_TIMEOUT_SECONDS=45
AI_MAX_TOKENS=1600
```

说明：

- 不配置 `GITHUB_TOKEN` 时，公开 PR 仍可通过 GitHub API 或 `.diff` fallback 尝试分析。
- 不配置 `AI_API_KEY` 时，系统会使用安全 fallback，仍能展示静态规则、风险评分和基础报告。
- 如果要自动评论到 GitHub PR，需要提供有仓库评论权限的 GitHub Token。

DeepSeek 示例配置：

```bash
AI_API_KEY=你的 DeepSeek API Key
AI_PROVIDER=auto
AI_API_BASE=https://api.deepseek.com/v1
AI_MODEL=deepseek-v4-flash
AI_DEEP_MODEL=deepseek-v4-flash
AI_TIMEOUT_SECONDS=20
AI_MAX_TOKENS=800
```

`AI_PROVIDER=auto` 会根据 `AI_API_BASE` 自动识别 DeepSeek、OpenAI 或其他 OpenAI-compatible 服务。也可以显式设置为 `deepseek`、`openai` 或 `openai-compatible`。`AI_MODEL` 用于 PR 总结，`AI_DEEP_MODEL` 用于文件级和跨文件审查。`AI_TIMEOUT_SECONDS` 和 `AI_MAX_TOKENS` 用来控制响应速度；模型超时或失败时，系统会自动回退到静态规则结果，避免任务卡死。

其他 OpenAI-compatible 模型服务示例：

```bash
AI_PROVIDER=openai-compatible
AI_API_KEY=你的兼容服务 API Key
AI_API_BASE=https://your-provider.example.com/v1
AI_MODEL=provider-fast-model
AI_DEEP_MODEL=provider-strong-model
```

兼容说明：当前客户端使用 OpenAI-compatible Chat Completions 协议。DeepSeek、OpenAI、以及提供 `/v1/chat/completions` 兼容接口的服务可以直接配置；不兼容该协议的原生 SDK 供应商需要后续新增 adapter。

代码层面已经拆出 provider adapter：

- `ModelConfig`：统一描述 provider、base URL、模型名、超时和输出长度。
- `ProviderStatus`：只暴露安全运行状态，不包含 API Key。
- `OpenAICompatibleAdapter`：封装 `/v1/chat/completions` 调用，DeepSeek、OpenAI 和兼容服务共用这一层。
- `AIClient`：只依赖 adapter 的 `complete()` 方法，后续接入 Gemini/Anthropic 原生 API 时可以新增 adapter，不需要改评审编排逻辑。

## 2. 启动服务

```bash
python main.py
```

默认访问地址：

```text
http://localhost:8000
```

主要页面：

| 页面 | 地址 | 用途 |
| --- | --- | --- |
| 首页 | `/` | 输入 GitHub PR URL，创建审查任务 |
| 任务列表 | `/tasks` | 查看历史任务 |
| 任务进度 | `/tasks/{task_id}` | 查看当前分析阶段 |
| 审查报告 | `/tasks/{task_id}/report` | 查看 PR 总结、风险文件、finding、置信度和建议 |
| 规则说明 | `/rules` | 查看 S001-S015 规则 |
| 评测仪表盘 | `/evaluation` | 查看 Golden Evaluation 和规则级质量指标 |

健康检查 API：

| API | 用途 |
| --- | --- |
| `/api/system/status` | 查看 AI Provider、模型名、超时、最大输出长度、GitHub Token 是否配置。该接口只返回布尔状态，不返回密钥内容。 |

## 3. 提交一次 PR 审查

1. 打开首页 `/`。
2. 在输入框填入 GitHub PR URL，例如：

```text
https://github.com/owner/repo/pull/123
```

3. 如需自动评论，勾选 `Auto-comment to GitHub PR`，并填写 GitHub Token。
4. 点击 `Start Review`。
5. 等待任务状态推进到 `DONE`。
6. 点击 `View Report` 查看报告。

完整分析链路：

```text
FETCHING_PR
-> BUILDING_CONTEXT
-> STATIC_SCAN
-> AI_PR_SUMMARY
-> AI_FILE_REVIEW
-> AI_CROSS_FILE
-> MERGING_RESULTS
-> GENERATING_REPORT
-> DONE
```

## 4. 如何读审查报告

报告页重点看四类信息：

1. `Risk Level`：当前 PR 的总体风险等级。
2. `File Risk Map`：哪些文件风险最高，优先审查哪里。
3. `Cockpit Quality Gate`：原始 finding 如何经过去重、置信度门控，最终变成可见结果和 GitHub 可评论结果。
4. `Findings`：每条问题包含严重级别、置信度、文件位置、原因、建议和证据链。

置信度门控规则：

| 置信度 | 处理方式 |
| --- | --- |
| `< 0.60` | 默认隐藏，避免低质量噪声 |
| `0.60 - 0.79` | 报告页可见，但不自动评论 |
| `>= 0.80` | 可进入 GitHub 评论候选 |
| `critical/high >= 0.70` | 高风险问题可进入 GitHub 评论候选 |

AI finding 还会经过 changed-line evidence gate：文件级 AI 问题需要尽量锚定到 PR 新增行或其附近。如果模型给出的行号不在 changed hunk 附近，系统会降低置信度并默认过滤低证据结果；如果能绑定到 changed line，报告会保留对应代码片段和置信度原因。这是为了减少普通 diff-to-LLM 容易出现的“合理但无证据”误报。

模型输出还会先经过结构校验：文件级 finding 必须包含有效的 `file`、正整数 `line`、`severity`、`title`、`reason`、`suggestion` 和数值型 `confidence`。`severity` 只接受 `critical/high/medium/low`，模型置信度会被裁剪到 `0.0-1.0`，不合格 finding 会计入 `invalid_finding_count`，不会进入去重、置信度门控或报告展示。

## 5. 使用 Golden Evaluation

Golden Evaluation 是本项目的质量评测集，用固定 PR/diff 样例衡量系统是否能正确发现问题，并控制误报。

评测边界需要明确：这里的 deterministic evaluation 主要衡量静态规则检测、去重、置信度门控和 GitHub-ready gating，不直接调用 LLM，因此不代表完整语义 AI Review 的全部质量。LLM 语义审查效果应结合真实 PR demo 和人工复核一起展示。

### 查看页面

打开：

```text
http://localhost:8000/evaluation
```

页面展示：

- 总样例数量，目前不少于 20 个。
- 真实公开 PR 回放集，目前不少于 5 个固定 snapshot。
- 全局 `Precision`、`Recall`。
- 误报数量 `False Positives`。
- 漏报数量 `Missed`。
- GitHub Ready finding 数量。
- 规则级质量表：每条规则的 expected、TP、FP、FN、precision、recall。
- 每个 case 的预期规则与实际命中规则。

### 查看 JSON API

```bash
curl http://localhost:8000/api/evaluation/golden
```

返回结构包含：

```json
{
  "total_cases": 20,
  "expected_total": 16,
  "true_positive_count": 16,
  "false_positive_count": 0,
  "false_negative_count": 0,
  "precision": 1.0,
  "recall": 1.0,
  "rule_metrics": {
    "S005": {
      "expected": 2,
      "true_positive": 2,
      "false_positive": 0,
      "false_negative": 0,
      "precision": 1.0,
      "recall": 1.0
    }
  }
}
```

真实公开 PR 回放 API：

```bash
curl http://localhost:8000/api/evaluation/real-pr-replay
```

该接口使用固定在本地的公开 PR diff snapshot，不依赖实时 GitHub 网络请求。当前包含：

| PR | 用途 |
| --- | --- |
| `localtunnel/localtunnel#339` | 源码变更无测试，验证 S015 test gap |
| `pallets/flask#5425` | 依赖文件变更，验证低风险控制 |
| `psf/requests#6700` | 测试文件变更，验证不误报源码风险 |
| `fastapi/fastapi#11400` | 文档变更，验证文档误报控制 |
| `pallets/click#2730` | 源码与测试一起变更，验证不误报测试缺失 |
 
首页的 `Try public PR sample` 会自动填入 `https://github.com/localtunnel/localtunnel/pull/339`，便于演示真实 PR 分析链路。

### Golden Evaluation 的展示价值

普通 diff-to-LLM 通常只把 diff 直接交给模型，缺少量化验收。本系统用 Golden Evaluation 展示：

- 哪些规则应该命中。
- 哪些命中是误报。
- 哪些预期问题被漏掉。
- 哪些 finding 经过置信度门控后才展示。
- 哪些 finding 足够可靠，可以进入 GitHub 评论候选。
- 真实 PR replay 中每条 finding 的来源 URL、规则、文件、行号和门控状态。

这能支撑答辩中的核心观点：系统不是简单包装 LLM，而是有质量门控和可回归评测的 AI PR Review 工具。

## 6. 本地测试

运行全部测试：

```bash
python -m pytest -q
```

只运行评测和页面相关测试：

```bash
python -m pytest tests/test_golden_evaluation.py tests/test_pages.py -q
```

前端原型构建：

```bash
cd frontend-prototype
npm run build
```

## 7. 继续扩展评测集

新增 golden case 的位置：

```text
app/golden_evaluation.py
```

每个 case 需要包含：

- `case_id`：稳定、可读、不可重复。
- `title`：说明这个样例验证什么。
- `changed_files`：模拟 PR 变更文件和 patch。
- `expected_rule_ids`：预期命中的规则集合。

新增或修改规则后，必须同步更新：

```text
tests/test_golden_evaluation.py
```

建议新增样例时同时覆盖：

- 真阳性：应该发现的问题。
- 误报控制：看起来像问题，但不应该报告。
- 边界情况：文档、测试文件、lockfile、删除文件、大 PR、低风险文件。

## 8. 常见问题

### 没有 AI Key 能否运行？

可以。系统会用静态规则和 fallback 摘要生成基础报告，但 AI 文件级分析和跨文件分析能力会受限。

### 为什么有些 finding 不会评论到 GitHub？

系统只把高置信或高风险 finding 作为 GitHub 评论候选，避免刷屏。中等置信 finding 仍会保留在报告页，供人工判断。

### 为什么文档里的代码示例不会触发规则？

静态扫描器默认跳过 `.md`、`.rst`、`.txt` 等文档文件，避免把说明文档中的示例代码当成生产代码误报。

### 这个工具相对普通 AI 审查的核心优势是什么？

核心优势是“规则 + AI + 置信度 + 评测闭环”：

- 规则负责确定性风险。
- AI 负责上下文解释和建议生成。
- 置信度门控控制噪声。
- Golden Evaluation 量化误报、漏报和规则效果。
