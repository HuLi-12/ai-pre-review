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
AI_API_KEY=sk_xxx
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

说明：

- 不配置 `GITHUB_TOKEN` 时，公开 PR 仍可通过 GitHub API 或 `.diff` fallback 尝试分析。
- 不配置 `AI_API_KEY` 时，系统会使用安全 fallback，仍能展示静态规则、风险评分和基础报告。
- 如果要自动评论到 GitHub PR，需要提供有仓库评论权限的 GitHub Token。

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

## 5. 使用 Golden Evaluation

Golden Evaluation 是本项目的质量评测集，用固定 PR/diff 样例衡量系统是否能正确发现问题，并控制误报。

### 查看页面

打开：

```text
http://localhost:8000/evaluation
```

页面展示：

- 总样例数量，目前不少于 20 个。
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

### Golden Evaluation 的展示价值

普通 diff-to-LLM 通常只把 diff 直接交给模型，缺少量化验收。本系统用 Golden Evaluation 展示：

- 哪些规则应该命中。
- 哪些命中是误报。
- 哪些预期问题被漏掉。
- 哪些 finding 经过置信度门控后才展示。
- 哪些 finding 足够可靠，可以进入 GitHub 评论候选。

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
