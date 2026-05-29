"""File risk scoring based on path, change size, and content keywords."""

from typing import List, Optional
from app.github_client import ChangedFile


# Risk weight by file path patterns
PATH_RULES = [
    # (keyword, score, reason)
    ("controller", 3, "Controller/API layer — interface change risk"),
    ("service", 3, "Service layer — business logic risk"),
    ("mapper", 3, "Mapper/Repository — data access risk"),
    ("repository", 3, "Repository — data access risk"),
    ("dao", 3, "DAO — data access risk"),
    ("sql", 2, "SQL change — data query risk"),
    ("mapper.xml", 3, "MyBatis XML — SQL execution risk"),
    ("model", 2, "Model/Entity — data structure change"),
    ("entity", 2, "Entity — data structure change"),
    ("dto", 1, "DTO — data transfer change"),
    ("vo", 1, "VO — data transfer change"),
    ("config", 2, "Configuration change — system impact"),
    ("schema", 2, "Schema change — database structure risk"),
    ("migration", 3, "Migration — database migration risk"),
    ("security", 3, "Security — auth/permission change"),
    ("test", -1, "Test file — lower risk"),
    ("spec", -1, "Test spec — lower risk"),
    ("readme", -2, "Documentation — minimal risk"),
    (".md", -2, "Documentation — minimal risk"),
]

# Keywords in added lines that increase risk
HIGH_RISK_CONTENT = [
    "delete", "drop", "truncate",  # Dangerous operations
    "grant", "revoke",              # Permission changes
    "password", "secret", "token",  # Sensitive data
    "exec(", "eval(",               # Code execution
    "raw_query", "rawSql",           # Raw SQL
    "flushdb", "flushall",           # Cache dangerous
]

DEPTH_THRESHOLDS = {
    "deep": 8,    # Score >= 8: full AI deep analysis
    "normal": 4,  # Score >= 4: normal AI analysis
    "skip": 0,    # Score < 4: summary only or skip
}


class FileRiskScorer:
    """Score files by risk level to prioritize AI analysis."""

    def score(self, changed_file: ChangedFile) -> dict:
        """Score a changed file and return risk assessment.

        Returns:
            {"score": int, "level": str, "reasons": [str]}
        """
        score = 0
        reasons = []
        path_lower = changed_file.file_path.lower()

        # 1. Path-based scoring
        for keyword, weight, reason in PATH_RULES:
            if keyword in path_lower:
                score += weight
                if weight > 0:
                    reasons.append(reason)

        # 2. Change size scoring
        if changed_file.additions > 200:
            score += 2
            reasons.append(f"Large addition ({changed_file.additions} lines)")
        elif changed_file.additions > 50:
            score += 1
            reasons.append(f"Medium addition ({changed_file.additions} lines)")

        if changed_file.deletions > 100:
            score += 1
            reasons.append(f"Large deletion ({changed_file.deletions} lines)")

        # 3. File type scoring
        if changed_file.file_path.endswith((".java", ".py", ".ts", ".js", ".go", ".rs")):
            score += 1
        elif changed_file.file_path.endswith((".json", ".xml", ".yaml", ".yml", ".properties")):
            score += 0  # Config files are neutral
        elif changed_file.file_path.endswith((".md", ".txt", ".gitignore", ".dockerfile")):
            score -= 2
            reasons.append("Documentation/config — low risk")

        # 4. Content keyword scoring
        if changed_file.patch:
            patch_lower = changed_file.patch.lower()
            for keyword in HIGH_RISK_CONTENT:
                if keyword in patch_lower:
                    score += 2
                    reasons.append(f"Contains risky keyword: '{keyword}'")
                    break  # Only count once per file

        # Clamp score
        score = max(-2, min(15, score))

        # Determine level
        if score >= DEPTH_THRESHOLDS["deep"]:
            level = "HIGH"
        elif score >= DEPTH_THRESHOLDS["normal"]:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "score": score,
            "level": level,
            "reasons": reasons[:5],  # Top 5 reasons
        }

    def should_deep_analyze(self, changed_file: ChangedFile) -> bool:
        """Determine if a file needs deep AI analysis."""
        result = self.score(changed_file)
        return result["score"] >= DEPTH_THRESHOLDS["normal"]

    def should_skip(self, changed_file: ChangedFile) -> bool:
        """Determine if a file can be skipped entirely."""
        result = self.score(changed_file)
        skip_extensions = {".md", ".txt", ".gitignore", ".lock", ".svg", ".png", ".jpg"}
        ext = changed_file.file_path.rsplit(".", 1)[-1].lower() if "." in changed_file.file_path else ""
        if ext in {e.lstrip(".") for e in skip_extensions}:
            return True
        return result["score"] < DEPTH_THRESHOLDS["skip"] and not changed_file.patch

    def get_analysis_depth(self, changed_file: ChangedFile) -> str:
        """Return analysis depth: 'deep', 'normal', 'skip'."""
        result = self.score(changed_file)
        if result["score"] >= DEPTH_THRESHOLDS["deep"]:
            return "deep"
        elif result["score"] >= DEPTH_THRESHOLDS["normal"]:
            return "normal"
        return "skip"
