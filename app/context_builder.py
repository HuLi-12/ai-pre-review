from typing import List, Dict, Optional
from app.github_client import ChangedFile, GitHubClient


class ReviewContext:
    """Multi-layer review context for AI analysis."""

    def __init__(self):
        self.pr_summary_context = ""
        self.file_diff_context: Dict[str, str] = {}
        self.file_full_context: Dict[str, str] = {}
        self.related_file_context: Dict[str, str] = {}
        self.repo_structure = ""
        self.file_relations: Dict[str, List[str]] = {}


class ContextBuilder:
    """Build multi-layer code context for AI review."""

    # Language-specific file relation mappings
    JAVA_RELATIONS = {
        "Controller": ["Service", "DTO", "VO", "Req", "Resp"],
        "Service": ["Mapper", "DO", "Entity", "Enum", "Config"],
        "Mapper": ["XML", "DO", "Entity"],
        "DTO": ["Controller"],
        "Config": ["properties", "yml", "yaml"],
    }

    PYTHON_RELATIONS = {
        "view": ["service", "serializer", "schema"],
        "service": ["repository", "model", "dao"],
        "model": ["migration", "schema"],
        "route": ["service", "schema"],
    }

    def __init__(self, github_client: GitHubClient, owner: str, repo: str, ref: str = "main"):
        self.github = github_client
        self.owner = owner
        self.repo = repo
        self.ref = ref

    def build(self, changed_files: List[ChangedFile]) -> ReviewContext:
        """Build complete review context"""
        context = ReviewContext()

        # Layer 1: diff context — what changed in each file
        for f in changed_files:
            context.file_diff_context[f.file_path] = f.patch

        # Layer 2: full file content for changed files
        for f in changed_files:
            if f.change_type != "removed" and f.raw_content:
                context.file_full_context[f.file_path] = f.raw_content

        # Layer 3: related files
        all_related = {}
        for f in changed_files:
            related = self._find_related_files(f.file_path)
            if related:
                all_related[f.file_path] = related
                for r_path in related:
                    if r_path not in context.file_full_context:
                        content = self.github.get_file_content(
                            self.owner, self.repo, r_path, self.ref
                        )
                        if content:
                            context.related_file_context[r_path] = content

        context.file_relations = all_related

        # Layer 4: repo structure summary
        context.repo_structure = self._get_repo_structure(changed_files)

        return context

    def _find_related_files(self, file_path: str) -> List[str]:
        """Find related files based on language conventions"""
        relations_map = self.JAVA_RELATIONS if file_path.endswith(".java") else \
            self.PYTHON_RELATIONS if file_path.endswith(".py") else {}

        if not relations_map:
            return []

        parts = file_path.replace("\\", "/").split("/")
        file_name = parts[-1] if parts else ""
        file_stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name

        related = []
        dir_path = "/".join(parts[:-1]) if len(parts) > 1 else ""

        for keyword, targets in relations_map.items():
            if keyword.lower() in file_stem.lower():
                for target in targets:
                    # Try common naming patterns
                    stem_lower = file_stem.lower().replace(keyword.lower(), target.lower())
                    # e.g., UserController -> UserService, UserDTO
                    prefix = file_stem.replace(keyword, "")
                    for ext in [".java", ".py", ".xml"]:
                        related_path = f"{dir_path}/{prefix}{target}{ext}" if prefix else \
                            f"{dir_path}/{file_stem.replace(keyword, target)}{ext}"
                        # Normalize: remove leading /
                        related_path = related_path.lstrip("/")
                        related.append(related_path)

        return related

    def _get_repo_structure(self, changed_files: List[ChangedFile]) -> str:
        """Generate a text summary of repository structure from changed files"""
        dirs = set()
        exts = set()
        for f in changed_files:
            parts = f.file_path.replace("\\", "/").split("/")
            if len(parts) > 1:
                dirs.add("/".join(parts[:-1]))
            if "." in f.file_path:
                exts.add(f.file_path.rsplit(".", 1)[1])

        structure_parts = []
        if dirs:
            structure_parts.append(f"Directories involved: {', '.join(sorted(dirs))}")
        if exts:
            structure_parts.append(f"File types: {', '.join(sorted(exts))}")

        return "\n".join(structure_parts)
