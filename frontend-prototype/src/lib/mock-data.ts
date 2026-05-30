import type { Finding, ChangedFile, TaskReport } from "./types"

export const mockFiles: ChangedFile[] = [
  { id: 1, file_path: "src/services/order_service.py", change_type: "modified", additions: 120, deletions: 45, risk_level: "high", risk_score: 85, analysis_depth: "deep" },
  { id: 2, file_path: "src/controllers/order_controller.py", change_type: "modified", additions: 68, deletions: 12, risk_level: "high", risk_score: 72, analysis_depth: "deep" },
  { id: 3, file_path: "src/models/order.py", change_type: "modified", additions: 30, deletions: 8, risk_level: "medium", risk_score: 55, analysis_depth: "normal" },
  { id: 4, file_path: "src/repositories/order_repo.py", change_type: "modified", additions: 45, deletions: 20, risk_level: "medium", risk_score: 48, analysis_depth: "normal" },
  { id: 5, file_path: "src/utils/validators.py", change_type: "modified", additions: 15, deletions: 5, risk_level: "low", risk_score: 25, analysis_depth: "normal" },
  { id: 6, file_path: "tests/test_order_service.py", change_type: "added", additions: 85, deletions: 0, risk_level: "low", risk_score: 10, analysis_depth: "skip" },
  { id: 7, file_path: "README.md", change_type: "modified", additions: 3, deletions: 1, risk_level: "low", risk_score: 5, analysis_depth: "skip" },
]

export const mockFindings: Finding[] = [
  {
    id: 1, file_path: "src/services/order_service.py", line_number: 156, finding_type: "S011", severity: "high",
    title: "循环内数据库查询 (N+1)",
    reason: "在 for 循环内执行 db.query(OrderItem).filter(...).all()，每次迭代都会发起一次数据库查询，导致 N+1 性能问题。",
    suggestion: "使用 JOIN 或 IN 查询批量获取数据：OrderItem.query.filter(OrderItem.order_id.in_(order_ids)).all()",
    confidence: 0.92, status: "open",
    evidence: [
      { type: "changed_file", label: "Changed File", content: "src/services/order_service.py" },
      { type: "line_number", label: "Line", content: "156" },
      { type: "rule_match", label: "Static Rule", content: "S011: loop_db_call" },
      { type: "confidence", label: "Confidence Gate", content: "92% (high) — visible + GitHub-ready" },
    ],
  },
  {
    id: 2, file_path: "src/controllers/order_controller.py", line_number: 42, finding_type: "S008", severity: "high",
    title: "新增 API 缺少权限验证",
    reason: "新增端点 POST /api/orders/batch-cancel 未添加 @require_auth 或 @require_role 装饰器，存在越权操作风险。",
    suggestion: "添加 @require_auth 和 @require_role('admin') 装饰器，确保只有授权用户可访问。",
    confidence: 0.88, status: "open",
    evidence: [
      { type: "changed_file", label: "Changed File", content: "src/controllers/order_controller.py" },
      { type: "line_number", label: "Line", content: "42" },
      { type: "rule_match", label: "Static Rule", content: "S008: missing_auth_check" },
      { type: "confidence", label: "Confidence Gate", content: "88% (high) — visible + GitHub-ready" },
    ],
  },
  {
    id: 3, file_path: "src/services/order_service.py", line_number: 201, finding_type: "S013", severity: "high",
    title: "多次数据库写入缺少事务",
    reason: "update_order() 方法连续执行了3次 SQL 写操作（UPDATE order, INSERT order_log, UPDATE inventory）但未使用事务包裹，中间步骤失败会导致数据不一致。",
    suggestion: "使用 @transactional 装饰器或将写操作放入 db.session.begin_nested() 上下文管理器中。",
    confidence: 0.85, status: "open",
    evidence: [
      { type: "changed_file", label: "Changed File", content: "src/services/order_service.py" },
      { type: "line_number", label: "Line", content: "201" },
      { type: "ai_source", label: "AI Source", content: "cross-file analysis" },
      { type: "confidence", label: "Confidence Gate", content: "85% (high) — visible + GitHub-ready" },
    ],
  },
  {
    id: 4, file_path: "src/repositories/order_repo.py", line_number: 88, finding_type: "S014", severity: "critical",
    title: "DELETE 语句缺少 WHERE 条件",
    reason: "清空表操作使用了无条件的 DELETE FROM order_items，在生产环境中可能导致数据全部丢失。",
    suggestion: "添加 WHERE 条件限制删除范围，或使用软删除标记（is_deleted 字段）。",
    confidence: 0.85, status: "open",
    evidence: [
      { type: "changed_file", label: "Changed File", content: "src/repositories/order_repo.py" },
      { type: "line_number", label: "Line", content: "88" },
      { type: "rule_match", label: "Static Rule", content: "S014: unsafe_delete_or_update" },
      { type: "confidence", label: "Confidence Gate", content: "85% (critical) — visible + GitHub-ready" },
    ],
  },
  {
    id: 5, file_path: "src/services/order_service.py", line_number: 12, finding_type: "S001", severity: "medium",
    title: "遗留的调试输出",
    reason: "存在 print(f\"order data: {order}\") 调试语句，在生产代码中应使用日志框架。",
    suggestion: "替换为 logger.debug(\"order data: %s\", order) 或直接移除。",
    confidence: 0.75, status: "open",
    evidence: [
      { type: "changed_file", label: "Changed File", content: "src/services/order_service.py" },
      { type: "line_number", label: "Line", content: "12" },
      { type: "rule_match", label: "Static Rule", content: "S001: hardcoded_print" },
      { type: "confidence", label: "Confidence Gate", content: "75% (medium) — visible in report" },
    ],
  },
  {
    id: 6, file_path: "src/utils/validators.py", line_number: 5, finding_type: "S002", severity: "low",
    title: "遗留的 FIXME 注释",
    reason: "代码中包含 # FIXME: validate edge cases 注释，需确认是否还有待办事项未处理。",
    suggestion: "确认问题已处理后移除此注释，或创建 Issue 跟踪。",
    confidence: 0.45, status: "open",
    evidence: [
      { type: "changed_file", label: "Changed File", content: "src/utils/validators.py" },
      { type: "line_number", label: "Line", content: "5" },
      { type: "rule_match", label: "Static Rule", content: "S002: todo_fixme" },
      { type: "confidence", label: "Confidence Gate", content: "45% (low) — filtered by default" },
    ],
  },
]

export const mockReport: TaskReport = {
  task_id: 142,
  pr_url: "https://github.com/org/repo/pull/142",
  pr_title: "feat: order batch processing pipeline",
  risk_level: "HIGH",
  merge_suggestion: "建议修复 high 及以上风险后再合并",
  summary: "本次 PR 在订单服务中新增了批量处理功能，涉及服务层、控制器层和仓储层的修改。主要变更包括：批量取消订单 API、订单状态更新逻辑、以及相关的数据访问方法。共扫描 7 个文件，发现 6 个问题（1 critical、3 high、1 medium、1 low）。",
  review_confidence: 88,
  total_raw: 18,
  total_deduped: 9,
  total_visible: 6,
  total_github_ready: 4,
  key_focus_points: [
    "DELETE 语句缺少 WHERE 条件 - 可能导致数据丢失",
    "循环内数据库查询 (N+1) - 性能风险",
    "新增 API 缺少权限验证 - 越权风险",
    "多次数据库写入缺少事务 - 数据一致性问题",
  ],
  test_suggestions: [
    "建议为新增的 order_service 逻辑补充单元测试",
    "建议为 batch-cancel 端点补充集成测试",
  ],
}
