# Agent Morph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 `agent-morph` Claude Code 插件，让用户用一句话或资源输入生成链式闭环的 Claude Code 智能体包。

**Architecture:** 插件自身采用 skill-driven 架构：主 skill 负责流程编排，5 个 agents 分别负责资源读取、调研、架构、构建、验证，2 个 scripts 处理确定性分类和结构校验，Stop hook 防止长流程提前停止。生成物不是默认插件，而是受约束的智能体包，必须从主 skill 可达所有组件。

**Tech Stack:** Claude Code plugin 目录结构、Markdown frontmatter、Python 3 标准库、JSON、superpowers 流程、plugin-dev 组件规范。

---

## 文件结构

本计划会创建以下文件：

```text
.claude-plugin/plugin.json
skills/agent-morph/SKILL.md
agents/resource-reader.md
agents/researcher.md
agents/agent-architect.md
agents/agent-builder.md
agents/agent-validator.md
scripts/detect-input-type.py
scripts/validate-agent-package.py
hooks/hooks.json
hooks/scripts/stop-guard.py
README.md
```

职责边界：

- `.claude-plugin/plugin.json`：插件元信息。
- `skills/agent-morph/SKILL.md`：唯一用户入口，只编排，不做重活。
- `agents/resource-reader.md`：读取和归一化输入资料。
- `agents/researcher.md`：调研工具、MCP、开源项目、最佳实践。
- `agents/agent-architect.md`：设计目标智能体包和组件链路。
- `agents/agent-builder.md`：基于确认设计、superpowers、plugin-dev 生成目标智能体包。
- `agents/agent-validator.md`：基于 superpowers、plugin-dev、脚本校验生成物。
- `scripts/detect-input-type.py`：确定性判断输入类型。
- `scripts/validate-agent-package.py`：确定性校验生成物结构和链式闭环。
- `hooks/hooks.json`：注册 Stop hook。
- `hooks/scripts/stop-guard.py`：阻止 agent-morph 工作流过早停止。
- `README.md`：中文说明安装、使用、流程、生成物结构和限制。

---

### Task 1: 创建插件基础结构和 manifest

**Files:**
- Create: `.claude-plugin/plugin.json`

- [ ] **Step 1: 创建目录**

Run:

```bash
mkdir -p .claude-plugin skills/agent-morph agents scripts hooks/scripts
```

Expected: 命令成功，无输出。

- [ ] **Step 2: 写入 plugin.json**

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "agent-morph",
  "version": "0.1.0",
  "description": "把用户需求或资源自动转换成链式闭环的 Claude Code 智能体包。",
  "author": {
    "name": "ablecheng"
  },
  "keywords": [
    "agent",
    "claude-code",
    "plugin",
    "skills",
    "automation"
  ]
}
```

- [ ] **Step 3: 验证 JSON 可解析**

Run:

```bash
python3 -m json.tool .claude-plugin/plugin.json >/tmp/agent-morph-plugin-json.out
```

Expected: 命令成功，无 stderr。

---

### Task 2: 实现输入类型检测脚本

**Files:**
- Create: `scripts/detect-input-type.py`

- [ ] **Step 1: 写入脚本**

Create `scripts/detect-input-type.py`:

```python
#!/usr/bin/env python3
"""检测 agent-morph 用户输入类型。"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def detect_input_type(raw: str) -> dict[str, object]:
    value = raw.strip()

    if not value:
        return {"type": "natural_language", "value": value, "confidence": 0.5}

    if re.match(r"^https?://(www\.)?github\.com/[^/\s]+/[^/\s#?]+", value):
        return {"type": "github_repo", "value": value, "confidence": 0.96}

    if re.match(r"^https?://", value):
        lower = value.lower()
        file_extensions = (
            ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".json", ".yaml", ".yml",
            ".txt", ".md", ".zip", ".tar", ".gz", ".py", ".js", ".ts"
        )
        clean_url = lower.split("?", 1)[0].split("#", 1)[0]
        if clean_url.endswith(file_extensions):
            return {"type": "file_url", "value": value, "confidence": 0.9}
        return {"type": "web_url", "value": value, "confidence": 0.88}

    expanded = os.path.expanduser(value)
    path = Path(expanded)
    if path.exists() and path.is_dir():
        return {"type": "local_path", "value": str(path), "confidence": 0.95}
    if path.exists() and path.is_file():
        return {"type": "local_file", "value": str(path), "confidence": 0.95}

    if value.startswith(("/", "./", "../", "~/")):
        return {"type": "local_path", "value": expanded, "confidence": 0.65}

    return {"type": "natural_language", "value": value, "confidence": 0.82}


def main() -> int:
    raw = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    print(json.dumps(detect_input_type(raw), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 赋予执行权限**

Run:

```bash
chmod +x scripts/detect-input-type.py
```

Expected: 命令成功，无输出。

- [ ] **Step 3: 验证自然语言检测**

Run:

```bash
python3 scripts/detect-input-type.py '帮我做一个财报分析智能体'
```

Expected output contains:

```json
"type": "natural_language"
```

- [ ] **Step 4: 验证 GitHub URL 检测**

Run:

```bash
python3 scripts/detect-input-type.py 'https://github.com/anthropics/claude-code'
```

Expected output contains:

```json
"type": "github_repo"
```

---

### Task 3: 实现生成物结构校验脚本

**Files:**
- Create: `scripts/validate-agent-package.py`

- [ ] **Step 1: 写入脚本**

Create `scripts/validate-agent-package.py`:

```python
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
```

- [ ] **Step 2: 赋予执行权限**

Run:

```bash
chmod +x scripts/validate-agent-package.py
```

Expected: 命令成功，无输出。

- [ ] **Step 3: 用临时合法包验证 pass**

Run:

```bash
rm -rf /tmp/agent-morph-valid && mkdir -p /tmp/agent-morph-valid/skills/main && cat > /tmp/agent-morph-valid/README.md <<'EOF'
# 测试包

主 skill: skills/main/SKILL.md
EOF
cat > /tmp/agent-morph-valid/skills/main/SKILL.md <<'EOF'
---
name: main
description: 测试主 skill。
---

执行主流程。
EOF
python3 scripts/validate-agent-package.py /tmp/agent-morph-valid
```

Expected output contains:

```json
"status": "pass"
```

- [ ] **Step 4: 用临时非法包验证 fail**

Run:

```bash
rm -rf /tmp/agent-morph-invalid && mkdir -p /tmp/agent-morph-invalid/scripts && touch /tmp/agent-morph-invalid/scripts/orphan.py && python3 scripts/validate-agent-package.py /tmp/agent-morph-invalid
```

Expected: 命令退出码为 1，输出包含：

```json
"status": "fail"
```

---

### Task 4: 实现主 skill

**Files:**
- Create: `skills/agent-morph/SKILL.md`

- [ ] **Step 1: 写入主 skill**

Create `skills/agent-morph/SKILL.md`:

```markdown
---
name: agent-morph
description: 当用户想把一句话需求、开源项目、本地代码路径、网页、文件 URL 或本地文件转换成 Claude Code 智能体包时使用。触发场景包括“帮我生成一个智能体”、“把这个项目转换成 Claude Code agents”、“根据这个需求构建 agent”、“agent-morph”。
argument-hint: <需求描述 | URL | 本地路径 | 文件路径>
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, Agent, Skill
---

# Agent Morph 主流程

你是 agent-morph 的主编排器。你的职责是把用户输入转换成一个完整、链式闭环、可验证的 Claude Code 智能体包。不要在主会话里做重活；重活分派给专门 agents。

## 硬约束

1. 生成物不是默认插件，而是 Claude Code 智能体包。
2. 生成物根目录只允许：`skills/`、`agents/`、`MCP/`、`hooks/`、`scripts/`、`README.md`。
3. 每个生成组件必须从主 skill 工作流可达，禁止孤立组件。
4. 构建阶段必须遵循 superpowers 开发流程。
5. 验证阶段必须遵循 superpowers completion 前验证纪律。
6. skill、agent、hook、MCP 定义必须参考 plugin-dev 最佳实践。
7. 所有文件默认使用中文，除非用户明确要求英文。

## 工作流

### 1. 输入分类

先运行：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/detect-input-type.py "$ARGUMENTS"
```

如果环境无法展开 `${CLAUDE_PLUGIN_ROOT}`，使用插件根目录下的 `scripts/detect-input-type.py`。

### 2. 资源读取

分派 `resource-reader`，输入包括：

- 用户原始输入
- 输入类型检测结果
- 当前工作目录

要求 `resource-reader` 输出：

```text
- 输入类型
- 原始资源位置
- 资源摘要
- 关键能力
- 可复用模式
- 缺失信息
- 建议调研问题
```

### 3. 需求澄清

围绕三个问题澄清：

1. 目标：最终智能体要完成什么？输出什么？是否有特殊格式？
2. 数据：需要哪些数据？来自用户输入、互联网、脚本、MCP，还是其他来源？如何处理？
3. 输入：未来用户如何调用这个智能体？一句话、文件、路径、URL，还是混合输入？

如果需要向用户提问，使用 AskUserQuestion。每组选项都必须包含一个“你自动调研”选项。

### 4. 调研

如果存在不确定点，分派一个或多个 `researcher`。调研范围包括：

- 现成 MCP
- 可复用开源项目
- 可复用库 / 工具
- 目标领域最佳实践
- 特殊输出格式工具
- Claude Code 组件规范

### 5. 架构设计

分派 `agent-architect`。要求输出：

```text
- 目标智能体名称
- 目标
- 预期用户输入
- 预期最终输出
- 数据来源
- 数据处理流程
- 组件列表
- 组件链路
- 目录结构
- 风险和假设
- 验证标准
```

组件链路必须说明每个组件：

- 被谁调用
- 调用谁
- 输入是什么
- 输出给谁

### 6. 最终确认

向用户展示最终确认版方案。用户确认后，写入：

```text
<english-agent-name>-confirm-design.md
```

### 7. 构建

分派 `agent-builder`。明确要求：

- 读取确认设计文档
- 使用 superpowers 流程制定和执行构建
- 使用 plugin-dev 规范生成 skills、agents、hooks、MCP、scripts、README
- 只生成确认设计里需要的组件
- 不允许生成孤立组件

### 8. 验证

分派 `agent-validator`。明确要求：

- 使用 superpowers 验证纪律
- 运行 `scripts/validate-agent-package.py <generated-package-root>`
- 检查链式闭环
- 检查 plugin-dev 组件质量
- 输出 pass/fail 验证报告

### 9. 最终输出

只在验证完成后输出：

```text
- 生成物路径
- 确认设计文档路径
- 验证状态
- 必须修复项，如有
- 使用方式
```

不要在验证前声称完成。
```

- [ ] **Step 2: 检查 skill 文件存在**

Run:

```bash
test -f skills/agent-morph/SKILL.md
```

Expected: 命令成功，无输出。

---

### Task 5: 实现 resource-reader agent

**Files:**
- Create: `agents/resource-reader.md`

- [ ] **Step 1: 写入 agent 文件**

Create `agents/resource-reader.md`:

```markdown
---
name: resource-reader
description: 当 agent-morph 需要读取和归一化用户输入资源时使用，包括自然语言需求、GitHub URL、本地代码路径、网页 URL、文件 URL、本地文件路径。此 agent 不设计最终智能体，只产出资源摘要和调研问题。
tools: Read, Glob, Grep, Bash, WebFetch, WebSearch
model: sonnet
color: blue
---

# Resource Reader

你负责读取用户提供的原始资源，并把它归一化为 agent-morph 后续步骤可使用的摘要。不要设计最终智能体，不要生成文件。

## 输入

你会收到：

```text
- 用户原始输入
- 输入类型检测结果
- 当前工作目录
```

## 处理规则

### natural_language

提取：

- 显性目标
- 隐含目标
- 预期输出
- 可能需要的数据
- 不确定点

### github_repo

优先读取公开页面或用户已提供的本地内容。需要 clone 时，只提出建议或请求主流程授权；不要自行做破坏性操作。

提取：

- 项目用途
- 核心模块
- 可复用工作流
- 可复用 agent/skill/script 设计
- 依赖和运行方式

### local_path

使用 Glob/Grep/Read 探索结构。优先读取 README、docs、配置文件、入口文件。避免读取大型无关文件。

### web_url

使用可用网页工具读取内容。遇到登录、权限或动态页面限制时，如实说明。

### file_url / local_file

按文件类型选择合适工具读取或建议转换。大型文件先摘要，不要倾倒全文。

## 输出格式

必须按以下格式输出：

```text
## 资源摘要
- 输入类型：
- 原始位置：
- 主题：
- 关键能力：
- 可复用模式：
- 明确约束：
- 缺失信息：
- 建议调研问题：
```
```

- [ ] **Step 2: 检查 frontmatter**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('agents/resource-reader.md')
s = p.read_text(encoding='utf-8')
assert s.startswith('---\n') and '\n---\n' in s[4:]
PY
```

Expected: 命令成功，无输出。

---

### Task 6: 实现 researcher agent

**Files:**
- Create: `agents/researcher.md`

- [ ] **Step 1: 写入 agent 文件**

Create `agents/researcher.md`:

```markdown
---
name: researcher
description: 当 agent-morph 已完成初步需求澄清，但仍需要调研现成 MCP、开源项目、工具库、特殊输出格式方案、领域最佳实践或 Claude Code 组件规范时使用。此 agent 只做调研和推荐，不生成目标智能体文件。
tools: WebSearch, WebFetch, Read, Glob, Grep, Bash
model: sonnet
color: purple
---

# Researcher

你负责调研 agent-morph 设计中的不确定点，并给出可执行建议。不要生成最终智能体文件。

## 输入

```text
- 已澄清需求
- resource-reader 摘要
- 不确定问题清单
```

## 调研范围

按问题需要调研：

- 是否有现成 MCP server
- 是否有成熟开源项目可参考
- 是否有可复用库或脚本工具
- 特殊文件 / 格式输出应使用什么工具
- 目标领域专家通常如何处理
- Claude Code skills / agents / hooks / MCP 的约束和最佳实践

## 输出格式

每个问题必须输出：

```text
## 调研问题：<问题>
- 结论：
- 可选方案：
- 推荐方案：
- 取舍理由：
- 可复用工具 / MCP / 库：
- 对目标智能体设计的影响：
- 仍不确定的点：
```

## 约束

- 不编造不存在的 MCP 或库。
- 不把 MCP 作为默认方案；只有现成 MCP 确实适合时才推荐。
- 不建议创建新的 MCP server。
- 如资料不足，明确说明不足。
```

- [ ] **Step 2: 检查 frontmatter**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('agents/researcher.md')
s = p.read_text(encoding='utf-8')
assert s.startswith('---\n') and '\n---\n' in s[4:]
PY
```

Expected: 命令成功，无输出。

---

### Task 7: 实现 agent-architect agent

**Files:**
- Create: `agents/agent-architect.md`

- [ ] **Step 1: 写入 agent 文件**

Create `agents/agent-architect.md`:

```markdown
---
name: agent-architect
description: 当 agent-morph 需要把澄清后的需求和调研结果转成目标 Claude Code 智能体包设计时使用。此 agent 负责组件划分、数据流、组件链路、目录结构和验证标准，不直接生成最终文件。
tools: Read, Write, Grep, Glob
model: opus
color: green
---

# Agent Architect

你负责设计目标 Claude Code 智能体包。你不直接生成最终组件文件，只输出可确认的设计方案。

## 输入

```text
- 用户确认后的目标
- resource-reader 摘要
- researcher 调研结果
- 用户偏好和约束
```

## 设计硬约束

1. 目标智能体包根目录只允许：`skills/`、`agents/`、`MCP/`、`hooks/`、`scripts/`、`README.md`。
2. 必须有主 skill。
3. 所有组件必须链式闭环。
4. 每个子 skill、agent、script、MCP、hook 都必须有调用方。
5. MCP 只使用现成 MCP，不创造新 MCP。
6. 固定流程、结构化处理、大批量处理优先脚本化。
7. 主 skill 只编排，不承担重执行。

## 输出格式

必须输出以下章节：

```text
# <目标智能体名称> 确认设计

## 1. 目标

## 2. 预期用户输入

## 3. 预期最终输出

## 4. 数据来源

## 5. 数据处理流程

## 6. 组件列表
| 组件 | 类型 | 作用 | 调用方 | 被调用对象 |

## 7. 组件链路
用文本树说明从主 skill 到所有组件的可达路径。

## 8. 目录结构

## 9. 构建要求
说明 agent-builder 必须如何使用 superpowers 和 plugin-dev。

## 10. 验证标准
说明 agent-validator 必须检查什么。

## 11. 风险和假设
```

## 质量门禁

输出前自检：

- 是否每个组件都有调用方？
- 是否存在孤立脚本或子 skill？
- 是否主 skill 能触达所有组件？
- 是否有不必要目录？
- 是否把插件和智能体包混为一谈？
```

- [ ] **Step 2: 检查 frontmatter**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('agents/agent-architect.md')
s = p.read_text(encoding='utf-8')
assert s.startswith('---\n') and '\n---\n' in s[4:]
PY
```

Expected: 命令成功，无输出。

---

### Task 8: 实现 agent-builder agent

**Files:**
- Create: `agents/agent-builder.md`

- [ ] **Step 1: 写入 agent 文件**

Create `agents/agent-builder.md`:

```markdown
---
name: agent-builder
description: 当 agent-morph 已获得用户确认的 *-confirm-design.md，需要生成目标 Claude Code 智能体包文件时使用。此 agent 必须基于 superpowers 开发流程和 plugin-dev 组件规范生成文件，并禁止孤立组件。
tools: Read, Write, Edit, Bash, Glob, Grep, Skill
model: opus
color: orange
---

# Agent Builder

你负责根据确认设计生成目标 Claude Code 智能体包。

## 输入

```text
- <english-agent-name>-confirm-design.md 路径
- 目标输出目录
```

## 强制流程

1. 先读取确认设计。
2. 使用或遵循 superpowers 的计划 / 执行流程。
3. 生成前列出组件链路。
4. 只生成确认设计中出现且被链路引用的组件。
5. 根据 plugin-dev 最佳实践生成 skill、agent、hook、MCP、README。
6. 生成后调用 agent-validator，不自行宣布完成。

## 生成规则

目标包根目录只允许：

```text
skills/
agents/
MCP/
hooks/
scripts/
README.md
```

必须生成：

- `README.md`
- 至少一个 `skills/<main-skill>/SKILL.md`

按需生成：

- `skills/<sub-skill>/SKILL.md`
- `agents/<agent-name>.md`
- `MCP/.mcp.json`
- `hooks/hooks.json`
- `hooks/scripts/...`
- `scripts/...`

## 每个文件必须说明链路位置

每个生成的 skill / agent / script / hook / MCP 说明中必须包含：

```text
- 调用方：
- 被调用对象：
- 输入：
- 输出：
- 在主流程中的位置：
```

## 禁止行为

- 不生成未被引用的 helper。
- 不创建确认设计外的目录。
- 不创造新 MCP server。
- 不把目标智能体包默认写成插件。
- 不跳过验证。
```

- [ ] **Step 2: 检查 frontmatter**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('agents/agent-builder.md')
s = p.read_text(encoding='utf-8')
assert s.startswith('---\n') and '\n---\n' in s[4:]
PY
```

Expected: 命令成功，无输出。

---

### Task 9: 实现 agent-validator agent

**Files:**
- Create: `agents/agent-validator.md`

- [ ] **Step 1: 写入 agent 文件**

Create `agents/agent-validator.md`:

```markdown
---
name: agent-validator
description: 当 agent-morph 生成目标 Claude Code 智能体包后，必须使用此 agent 验证结构、链式闭环、plugin-dev 组件质量和 superpowers completion 前验证要求。发现孤立组件时必须判定不可交付。
tools: Read, Bash, Glob, Grep, Skill
model: sonnet
color: red
---

# Agent Validator

你负责验证 agent-morph 生成的目标智能体包。不要替用户美化结果；不合格就明确 fail。

## 输入

```text
- 目标智能体包路径
- 对应的 *-confirm-design.md 路径
```

## 强制验证流程

1. 使用 superpowers 的 completion 前验证纪律。
2. 运行结构校验脚本：

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate-agent-package.py <target-package-root>
```

3. 检查确认设计与生成物是否一致。
4. 检查每个组件是否从主 skill 可达。
5. 检查 skill / agent / hook / MCP 是否符合 plugin-dev 质量要求。
6. 输出 pass/fail。

## 验证清单

| 区域 | 检查内容 |
|---|---|
| 结构 | 根目录只包含允许项 |
| 主 skill | 存在，且能启动完整工作流 |
| Skills | 触发描述和调用关系清楚 |
| Agents | Frontmatter、职责、工具、输出格式清楚 |
| Scripts | 每个脚本都有调用方和参数契约 |
| MCP | 只引用现有 MCP，且有调用方 |
| Hooks | 事件绑定合法，工作流目的明确 |
| README | 说明安装、使用和组件链路 |
| 链式闭环 | 所有组件可从主 skill 触达 |
| 设计一致性 | 生成文件符合确认设计 |

## 输出格式

```text
# 验证报告

## 状态
pass 或 fail

## 通过项

## 失败项

## 孤立组件

## 必须修复项

## 建议优化项

## 最终结论
```

## 判定规则

只要出现以下任一情况，状态必须是 fail：

- 缺少主 skill
- 根目录包含不允许项
- 任一组件孤立
- JSON 配置不可解析
- 生成物与确认设计明显不一致
```

- [ ] **Step 2: 检查 frontmatter**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('agents/agent-validator.md')
s = p.read_text(encoding='utf-8')
assert s.startswith('---\n') and '\n---\n' in s[4:]
PY
```

Expected: 命令成功，无输出。

---

### Task 10: 实现 Stop guard hook

**Files:**
- Create: `hooks/hooks.json`
- Create: `hooks/scripts/stop-guard.py`

- [ ] **Step 1: 写入 hooks.json**

Create `hooks/hooks.json`:

```json
{
  "Stop": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/stop-guard.py",
          "timeout": 10
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: 写入 stop-guard.py**

Create `hooks/scripts/stop-guard.py`:

```python
#!/usr/bin/env python3
"""agent-morph Stop hook：阻止工作流过早停止。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MAX_BLOCKS = 2
STATE_FILE = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".agent-morph-state.json"


def read_stdin_json() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    _event = read_stdin_json()
    state = load_state()

    if not state.get("active"):
        return 0

    required = [
        "confirm_design_written",
        "target_package_generated",
        "structure_validation_run",
        "validation_report_written",
        "final_instructions_returned",
    ]

    missing = [key for key in required if not state.get(key)]
    if not missing:
        return 0

    blocks = int(state.get("stop_blocks", 0))
    if blocks >= MAX_BLOCKS:
        return 0

    state["stop_blocks"] = blocks + 1
    save_state(state)

    print(
        "agent-morph 工作流尚未完成，禁止提前停止。缺失阶段：" + ", ".join(missing),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: 赋予执行权限**

Run:

```bash
chmod +x hooks/scripts/stop-guard.py
```

Expected: 命令成功，无输出。

- [ ] **Step 4: 验证 hooks.json 可解析**

Run:

```bash
python3 -m json.tool hooks/hooks.json >/tmp/agent-morph-hooks-json.out
```

Expected: 命令成功，无 stderr。

---

### Task 11: 编写 README

**Files:**
- Create: `README.md`

- [ ] **Step 1: 写入 README**

Create `README.md`:

```markdown
# agent-morph

agent-morph 是一个 Claude Code 插件，用于把用户的一句话需求、开源项目、本地代码、网页或文件转换成完整的 Claude Code 智能体包。

## 前置依赖

agent-morph 依赖：

- superpowers 插件：用于构建、执行计划、验证完成状态。
- plugin-dev 插件：用于遵循 skills、agents、hooks、MCP 等组件的结构约束和最佳实践。

## 安装

把本目录作为 Claude Code 插件目录加载。

```bash
cc --plugin-dir /path/to/agent-morph
```

## 使用

```text
/agent-morph 帮我做一个能分析财报的 Claude Code 智能体
/agent-morph https://github.com/example/project
/agent-morph ./local-project
/agent-morph ./requirements.pdf
```

## 支持输入类型

- 自然语言需求
- GitHub / 开源项目 URL
- 本地代码路径
- Web URL
- 文件 URL
- 本地文件路径

## 工作流

1. 输入分类。
2. 资源读取。
3. 需求澄清。
4. 多 agent 调研。
5. 最终确认设计。
6. 写入 `<english-agent-name>-confirm-design.md`。
7. 基于 superpowers 和 plugin-dev 生成目标智能体包。
8. 验证结构、质量和链式闭环。
9. 输出生成物路径和验证报告。

## 生成物结构

agent-morph 生成的是 Claude Code 智能体包，不默认等同于插件。生成物根目录只允许：

```text
skills/
agents/
MCP/
hooks/
scripts/
README.md
```

`skills/` 和 `README.md` 必须存在，其余目录只在确认设计需要时创建。

## 组件链式闭环规则

所有组件都必须从主 skill 工作流可达。

示例：

```text
主 skill
  -> subagent
      -> script
      -> 子 skill
  -> 另一个 subagent
      -> MCP
  -> hook
  -> 最终输出
```

禁止孤立组件：

- 没有调用方的子 skill
- 没有被分派的 agent
- 没有被引用的 script
- 没有使用说明的 MCP 配置
- 与主流程无关的 hook

## 插件自身组件

```text
.claude-plugin/plugin.json
skills/agent-morph/SKILL.md
agents/resource-reader.md
agents/researcher.md
agents/agent-architect.md
agents/agent-builder.md
agents/agent-validator.md
scripts/detect-input-type.py
scripts/validate-agent-package.py
hooks/hooks.json
hooks/scripts/stop-guard.py
```

## 限制

- agent-morph 不创造新的 MCP server。
- agent-morph 不保证所有外部 URL 都可访问。
- agent-morph 不生成允许目录以外的任意项目结构。
- 除非确认设计明确要求插件化打包，否则不把生成物默认视为 Claude Code 插件。

## 故障排查

### 输入类型识别不符合预期

运行：

```bash
python3 scripts/detect-input-type.py '<输入>'
```

### 生成物验证失败

运行：

```bash
python3 scripts/validate-agent-package.py <生成物目录>
```

根据输出中的 `errors` 修复结构、frontmatter 或组件链路问题。
```

- [ ] **Step 2: 检查 README 存在**

Run:

```bash
test -f README.md
```

Expected: 命令成功，无输出。

---

### Task 12: 全量验证插件结构

**Files:**
- Verify all created files

- [ ] **Step 1: 检查必需文件全部存在**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
required = [
    '.claude-plugin/plugin.json',
    'skills/agent-morph/SKILL.md',
    'agents/resource-reader.md',
    'agents/researcher.md',
    'agents/agent-architect.md',
    'agents/agent-builder.md',
    'agents/agent-validator.md',
    'scripts/detect-input-type.py',
    'scripts/validate-agent-package.py',
    'hooks/hooks.json',
    'hooks/scripts/stop-guard.py',
    'README.md',
]
missing = [p for p in required if not Path(p).exists()]
assert not missing, missing
print('all required files exist')
PY
```

Expected output:

```text
all required files exist
```

- [ ] **Step 2: 检查 JSON 文件**

Run:

```bash
python3 -m json.tool .claude-plugin/plugin.json >/tmp/agent-morph-plugin-json.out && python3 -m json.tool hooks/hooks.json >/tmp/agent-morph-hooks-json.out
```

Expected: 命令成功，无 stderr。

- [ ] **Step 3: 检查 Python 语法**

Run:

```bash
python3 -m py_compile scripts/detect-input-type.py scripts/validate-agent-package.py hooks/scripts/stop-guard.py
```

Expected: 命令成功，无 stderr。

- [ ] **Step 4: 检查 Markdown frontmatter**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
files = [Path('skills/agent-morph/SKILL.md'), *Path('agents').glob('*.md')]
for p in files:
    s = p.read_text(encoding='utf-8')
    assert s.startswith('---\n') and '\n---\n' in s[4:], f'missing frontmatter: {p}'
print('frontmatter ok')
PY
```

Expected output:

```text
frontmatter ok
```

- [ ] **Step 5: 运行脚本行为测试**

Run:

```bash
python3 scripts/detect-input-type.py 'https://github.com/anthropics/claude-code' | grep 'github_repo' && python3 scripts/detect-input-type.py '帮我做一个智能体' | grep 'natural_language'
```

Expected output contains:

```text
github_repo
natural_language
```

- [ ] **Step 6: 运行生成物校验脚本测试**

Run:

```bash
rm -rf /tmp/agent-morph-valid && mkdir -p /tmp/agent-morph-valid/skills/main && cat > /tmp/agent-morph-valid/README.md <<'EOF'
# 测试包

主 skill: skills/main/SKILL.md
EOF
cat > /tmp/agent-morph-valid/skills/main/SKILL.md <<'EOF'
---
name: main
description: 测试主 skill。
---

执行主流程。
EOF
python3 scripts/validate-agent-package.py /tmp/agent-morph-valid
```

Expected output contains:

```json
"status": "pass"
```

- [ ] **Step 7: 如当前目录是 git 仓库则提交；否则跳过**

Run:

```bash
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git status --short; else echo 'not a git repository, skip commit'; fi
```

Expected in current project:

```text
not a git repository, skip commit
```

---

## 自检结果

- Spec coverage：计划覆盖 manifest、主 skill、5 个 agents、2 个 scripts、Stop hook、README、结构验证、链式闭环、superpowers/plugin-dev 硬约束。
- Placeholder scan：无 TBD/TODO/implement later。
- Type consistency：脚本名、agent 名、目录名与确认设计一致。
