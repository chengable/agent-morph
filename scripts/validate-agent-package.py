#!/usr/bin/env python3
"""校验 agent-morph 生成的 Claude Code 智能体包。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ALLOWED_ROOT_ENTRIES = {"skills", "agents", "MCP", "hooks", "scripts", "README.md"}
OPTIONAL_DIRS = {"agents", "MCP", "hooks", "scripts"}


def has_frontmatter(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return text.startswith("---\n") and "\n---\n" in text[4:]


def list_components(root: Path) -> dict[str, list[str]]:
    components: dict[str, list[str]] = {
        "skills": [],
        "agents": [],
        "scripts": [],
        "hooks": [],
        "mcp": [],
    }

    skills_dir = root / "skills"
    if skills_dir.exists():
        for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
            components["skills"].append(str(skill_file.relative_to(root)))

    agents_dir = root / "agents"
    if agents_dir.exists():
        for agent_file in sorted(agents_dir.glob("*.md")):
            components["agents"].append(str(agent_file.relative_to(root)))

    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        for script_file in sorted(p for p in scripts_dir.rglob("*") if p.is_file()):
            components["scripts"].append(str(script_file.relative_to(root)))

    hooks_file = root / "hooks" / "hooks.json"
    if hooks_file.exists():
        components["hooks"].append(str(hooks_file.relative_to(root)))
    hooks_scripts = root / "hooks" / "scripts"
    if hooks_scripts.exists():
        for script_file in sorted(p for p in hooks_scripts.rglob("*") if p.is_file()):
            components["hooks"].append(str(script_file.relative_to(root)))

    mcp_file = root / "MCP" / ".mcp.json"
    if mcp_file.exists():
        components["mcp"].append(str(mcp_file.relative_to(root)))

    return components


def read_all_markdown(root: Path) -> str:
    chunks = []
    for path in sorted(root.rglob("*.md")):
        chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def check_references(root: Path, components: dict[str, list[str]]) -> list[str]:
    failures: list[str] = []
    corpus = read_all_markdown(root)

    for group, paths in components.items():
        for component_path in paths:
            if component_path == "README.md":
                continue
            name = Path(component_path).name
            parent = Path(component_path).parent.name
            candidates = {component_path, name, parent}
            if group == "skills" and name == "SKILL.md":
                candidates.add(parent)
            if not any(candidate in corpus for candidate in candidates):
                failures.append(f"组件未在 Markdown 链路中被引用: {component_path}")

    return failures


def validate(root: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    if not root.exists() or not root.is_dir():
        return {"status": "fail", "errors": [f"路径不存在或不是目录: {root}"], "warnings": []}

    root_entries = {p.name for p in root.iterdir()}
    unexpected = sorted(root_entries - ALLOWED_ROOT_ENTRIES)
    if unexpected:
        errors.append(f"根目录包含不允许的项目: {', '.join(unexpected)}")

    if not (root / "README.md").exists():
        errors.append("缺少 README.md")

    skills_dir = root / "skills"
    if not skills_dir.exists() or not skills_dir.is_dir():
        errors.append("缺少 skills/ 目录")
    else:
        skill_files = sorted(skills_dir.glob("*/SKILL.md"))
        if not skill_files:
            errors.append("skills/ 下至少需要一个 */SKILL.md")
        for skill_file in skill_files:
            if not has_frontmatter(skill_file):
                errors.append(f"skill 缺少 frontmatter: {skill_file.relative_to(root)}")

    agents_dir = root / "agents"
    if agents_dir.exists():
        for agent_file in sorted(agents_dir.glob("*.md")):
            if not has_frontmatter(agent_file):
                errors.append(f"agent 缺少 frontmatter: {agent_file.relative_to(root)}")

    hooks_json = root / "hooks" / "hooks.json"
    if hooks_json.exists():
        try:
            json.loads(hooks_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"hooks/hooks.json JSON 解析失败: {exc}")

    mcp_json = root / "MCP" / ".mcp.json"
    if mcp_json.exists():
        try:
            json.loads(mcp_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"MCP/.mcp.json JSON 解析失败: {exc}")

    for dirname in OPTIONAL_DIRS:
        directory = root / dirname
        if directory.exists() and directory.is_dir() and not any(directory.iterdir()):
            warnings.append(f"目录为空，建议删除或补全链路: {dirname}/")

    components = list_components(root)
    errors.extend(check_references(root, components))

    return {
        "status": "fail" if errors else "pass",
        "errors": errors,
        "warnings": warnings,
        "components": components,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate-agent-package.py <agent-package-root>", file=sys.stderr)
        return 2

    result = validate(Path(sys.argv[1]).resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
