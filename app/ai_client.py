import json
import re
from typing import Optional, List, Dict, Any
from config import settings
from app.ai_provider import OpenAICompatibleAdapter, build_model_config


class AIClient:
    """AI client wrapper supporting OpenAI-compatible APIs."""

    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None, adapter=None):
        self.config = build_model_config(settings, api_key=api_key, api_base=api_base)
        self.adapter = adapter or OpenAICompatibleAdapter(self.config)
        self.api_key = self.config.api_key
        self.model = self.config.model
        self.deep_model = self.config.deep_model

    def _call_llm(self, system_prompt: str, user_prompt: str,
                  model: Optional[str] = None, temperature: float = 0.1) -> str:
        """Call LLM with prompts and return text response"""
        if not self.adapter.enabled:
            return ""
        return self.adapter.complete(system_prompt, user_prompt, model=model, temperature=temperature)

    def _call_llm_json(self, system_prompt: str, user_prompt: str,
                       model: Optional[str] = None) -> dict:
        """Call LLM and parse JSON response"""
        text = self._call_llm(system_prompt, user_prompt, model)
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Extract JSON from LLM response (handles markdown fences)"""
        # Try to find JSON block inside ```json ... ```
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            text = json_match.group(1)

        # Try to find {...} or [...] from text
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find the outermost JSON object
            brace_start = text.find("{")
            brace_end = text.rfind("}")
            if brace_start >= 0 and brace_end > brace_start:
                try:
                    return json.loads(text[brace_start:brace_end + 1])
                except json.JSONDecodeError:
                    pass
            return {}

    # ---- Prompt Templates ----

    PR_SUMMARY_SYSTEM_PROMPT = """You are a senior code review expert. Based on the Pull Request information, summarize the changes.

Requirements:
1. Use concise language to explain the PR purpose
2. Categorize changes by module
3. Identify potential business impact scope
4. Mark files that need focused review
5. Do NOT fabricate content not present in the diff

Output JSON format:
{
  "one_line_summary": "<one sentence PR summary>",
  "module_changes": {
    "<module_name>": ["<change description>", ...]
  },
  "business_impact": ["<impact description>", ...],
  "risk_modules": ["<module name>", ...],
  "focus_files": ["<file path>", ...]
}"""

    FILE_REVIEW_SYSTEM_PROMPT = """You are a rigorous code review expert. Analyze the provided diff, file content, and related context.

Focus on:
1. Correctness issues — logic errors, null pointer risks, boundary conditions
2. Security issues — missing auth, injection risks, sensitive data exposure
3. Performance issues — N+1 queries, no pagination, repeated calls
4. Transaction & concurrency issues — race conditions, inconsistent transactions
5. Exception handling issues — swallowed exceptions, improper error handling
6. Maintainability issues — overly long methods, magic values, dead code
7. Test coverage issues — missing tests for new logic

Output requirements:
- Must output valid JSON
- Each finding must include: file, line, severity, title, reason, suggestion, confidence
- You are not limited to the static rule IDs. Static rules are deterministic signals; your job is to identify semantic and contextual review risks that may not match any predefined rule.
- Use source = ai_file and rule_id = null unless the finding is directly confirmed by a static rule.
- Use category such as correctness, security, performance, reliability, test, maintainability, architecture, api_contract, or data_consistency.
- Do not force-fit a finding into S001-S015.
- Only output issues with clear evidence
- Do NOT output generic code style advice
- Each suggestion must be concrete and actionable: name the exact fix, guard, API call, transaction, validation, or test to add.
- Tie the suggestion to the cited changed line or affected contract.
- Do not use generic suggestions such as "review carefully", "fix the issue", or "improve code quality".
- Low confidence issues should use note level, not blocking

Output JSON format:
{
  "file_summary": "<one sentence about this file>",
  "findings": [
    {
      "source": "ai_file",
      "rule_id": null,
      "category": "correctness|security|performance|reliability|test|maintainability",
      "file": "<file_path>",
      "line": <line_number>,
      "type": "correctness|security|performance|maintainability|test",
      "severity": "critical|high|medium|low",
      "title": "<short title>",
      "reason": "<detailed explanation>",
      "suggestion": "<concrete fix suggestion>",
      "confidence": <0.0-1.0>
    }
  ]
}"""

    CROSS_FILE_SYSTEM_PROMPT = """You are a senior architect. Analyze whether there are consistency issues across multiple files in this PR.

You are not limited to the static rule IDs. Static rules are deterministic signals, but your task is to identify semantic, contextual, and cross-file review risks that may not match any predefined rule.
For each finding, use source = ai_cross, rule_id = null, and a category such as architecture, api_contract, data_flow, data_consistency, reliability, or test. Do not force-fit a finding into S001-S015.
Each suggestion must be concrete and actionable. Tie the suggestion to the cited changed line or affected contract. Do not use generic suggestions such as "review carefully", "fix the issue", or "improve code quality".

Focus areas:
1. API parameter/return type changes — are callers updated accordingly?
2. DTO/VO/DO field changes — are database, Mapper, and frontend consistent?
3. State enum changes — are all branches covered?
4. Cache write/update/delete consistency
5. Post-transaction async task idempotency
6. New core logic — is there test coverage?

Output JSON format:
{
  "findings": [
    {
      "source": "ai_cross",
      "rule_id": null,
      "category": "architecture|api_contract|data_flow|data_consistency|reliability|test",
      "title": "<issue title>",
      "severity": "critical|high|medium|low",
      "files_involved": ["<file_path>", ...],
      "reason": "<detailed explanation>",
      "suggestion": "<fix suggestion>",
      "confidence": <0.0-1.0>
    }
  ]
}"""

    # ---- Review Methods ----

    def summarize_pr(self, pr_title: str, pr_description: str,
                     commit_messages: str, changed_files_summary: str) -> dict:
        """Stage 1: PR overall understanding and summary"""
        fallback = self._fallback_summary(pr_title, changed_files_summary)
        if not self.adapter.enabled:
            return fallback

        user_prompt = f"""PR Title: {pr_title}
PR Description: {pr_description}
Commit Messages: {commit_messages}
Changed Files:
{changed_files_summary}"""
        return self._call_llm_json(self.PR_SUMMARY_SYSTEM_PROMPT, user_prompt) or fallback

    def review_file(self, file_path: str, diff: str, full_content: str,
                    related_context: str, rule_findings: str) -> dict:
        """Stage 2: Analyze a single changed file"""
        fallback = {"file_summary": "AI review unavailable; static rules were used.", "findings": []}
        if not self.adapter.enabled:
            return fallback

        user_prompt = f"""File: {file_path}

Diff:
```diff
{diff[:8000]}
```

Full File Content:
```{file_path.rsplit('.', 1)[-1] if '.' in file_path else ''}
{full_content[:12000]}
```

Related Context:
{related_context[:3000]}

Static Rule Findings:
{rule_findings}"""
        return self._call_llm_json(self.FILE_REVIEW_SYSTEM_PROMPT, user_prompt, model=self.deep_model) or fallback

    def cross_file_analysis(self, file_contexts: Dict[str, str]) -> dict:
        """Stage 3: Cross-file consistency analysis"""
        fallback = {"findings": []}
        if not self.adapter.enabled:
            return fallback

        context_parts = []
        for file_path, content in file_contexts.items():
            context_parts.append(f"=== {file_path} ===\n{content[:3000]}")
        user_prompt = "Analyze the following files for cross-file consistency issues:\n\n" + \
                      "\n\n".join(context_parts)
        return self._call_llm_json(self.CROSS_FILE_SYSTEM_PROMPT, user_prompt, model=self.deep_model) or fallback

    @staticmethod
    def _fallback_summary(pr_title: str, changed_files_summary: str) -> dict:
        focus_files = []
        for line in changed_files_summary.splitlines():
            line = line.strip()
            if not line:
                continue
            focus_files.append(line.split(" ", 1)[0])

        return {
            "one_line_summary": pr_title or "AI summary unavailable; static analysis completed.",
            "module_changes": {"changed_files": focus_files[:20]} if focus_files else {},
            "business_impact": ["AI model unavailable; report is based on static rules and file risk signals."],
            "risk_modules": [],
            "focus_files": focus_files[:20],
        }
