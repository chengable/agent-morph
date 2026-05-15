# agent-morph

**[中文](#中文文档) | [English](#english-doc)**

---

<a id="中文文档"></a>

把用户需求或资源自动转换成链式闭环的 Claude Code 智能体包。

### 为什么做这个？

用 Claude Code 久了会发现一个痛点：**重复造轮子**。每次想做一个新智能体，都要从零开始 — 设计架构、写 skill、配 agent、调 hook、写验证脚本。这些工作大量重复，而且很容易漏掉关键步骤。

agent-morph 就是来解决这个问题的。给它一句话需求、一个开源项目、一份文档，它就能自动走完调研 → 设计 → 构建 → 验证全流程，产出一个结构完整、链路闭环、拿来即用的智能体包。

简单说：**你只管提需求，脏活累活交给它。**

## 前置依赖

agent-morph 依赖以下插件，请先安装：

```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

```bash
/plugin marketplace add claude-plugins-official/plugin-dev
/plugin install plugin-dev@plugin-dev
```

## 安装

```bash
/plugin marketplace add chengable/agent-morph
/plugin install agent-morph@agent-morph
```

## 使用

```text
/agent-morph 帮我做一个能分析财报的 Claude Code 智能体
/agent-morph https://github.com/example/project
/agent-morph ./local-project
/agent-morph ./requirements.pdf
```

## 支持输入类型

| 类型 | 示例 |
|------|------|
| 自然语言需求 | `帮我生成一个抓取新闻的智能体` |
| GitHub 仓库 URL | `https://github.com/user/repo` |
| 本地代码路径 | `./my-project` |
| 网页 URL | `https://example.com/docs` |
| 文件 URL | `https://example.com/spec.pdf` |
| 本地文件路径 | `./requirements.md` |

## 工作流

1. **输入分类** — 自动识别输入类型
2. **资源读取** — 提取关键信息和模式
3. **需求澄清** — 确认目标、数据、交互方式
4. **调研** — 搜索可复用的 MCP、库、最佳实践
5. **架构设计** — 规划组件列表和链路
6. **最终确认** — 生成设计文档，等用户确认
7. **构建** — 基于 superpowers + plugin-dev 生成智能体包
8. **验证** — 结构、质量、链式闭环检查
9. **输出** — 生成物路径 + 验证报告

## 生成物结构

agent-morph 生成的是 Claude Code 智能体包，根目录只包含：

```text
skills/       # 必须存在
agents/       # 按需
hooks/        # 按需
scripts/      # 按需
MCP/          # 按需
README.md     # 必须存在
```

生成物 README 会指导你把各目录放到 Claude Code 生效位置（如 `.claude/skills/`、`.claude/agents/`）。

## 组件链式闭环

所有生成组件必须从主 skill 可达，禁止孤立组件。每个组件都明确：

- 被谁调用
- 调用谁
- 输入是什么
- 输出给谁

## 故障排查

### 输入类型识别不符合预期

模型会自动判断输入类型（自然语言/URL/本地路径等）。如识别有误，请在输入中更明确地描述你的需求或提供完整路径/URL。

### 生成物验证失败

此脚本只用于验证 agent-morph 生成的目标智能体包，不用于验证插件源码。

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate-agent-package.py <生成物目录>
```

## 限制

- 不创造新的 MCP server
- 不保证所有外部 URL 都可访问
- 不生成允许目录以外的任意项目结构
- 除非确认设计明确要求，否则不把生成物默认视为 Claude Code 插件

## License

MIT

---

<a id="english-doc"></a>

Automatically transform user requirements or resources into chain-closed Claude Code agent packages.

### Why build this?

After using Claude Code extensively, one pain point becomes obvious: **reinventing the wheel**. Every time you want to build a new agent, you start from scratch — designing architecture, writing skills, configuring agents, tuning hooks, building validation scripts. It's repetitive and error-prone, with critical steps easily missed.

agent-morph exists to solve this. Give it a one-liner requirement, an open-source project, or a document, and it automatically runs through research → design → build → validation, producing a structurally complete, chain-closed, ready-to-use agent package.

In short: **you focus on the what, it handles the how.**

## Prerequisites

agent-morph depends on the following plugins. Install them first:

```bash
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

```bash
/plugin marketplace add claude-plugins-official/plugin-dev
/plugin install plugin-dev@plugin-dev
```

## Installation

```bash
/plugin marketplace add chengable/agent-morph
/plugin install agent-morph@agent-morph
```

## Usage

```text
/agent-morph Build me a financial report analysis agent
/agent-morph https://github.com/example/project
/agent-morph ./local-project
/agent-morph ./requirements.pdf
```

## Supported Input Types

| Type | Example |
|------|---------|
| Natural language | `Build me a news scraping agent` |
| GitHub repo URL | `https://github.com/user/repo` |
| Local code path | `./my-project` |
| Web URL | `https://example.com/docs` |
| File URL | `https://example.com/spec.pdf` |
| Local file path | `./requirements.md` |

## Workflow

1. **Input classification** — Auto-detect input type
2. **Resource reading** — Extract key info and patterns
3. **Requirement clarification** — Confirm goals, data, interaction
4. **Research** — Search for reusable MCP, libraries, best practices
5. **Architecture design** — Plan component list and chains
6. **Final confirmation** — Generate design doc, await user approval
7. **Build** — Generate agent package using superpowers + plugin-dev
8. **Validation** — Structure, quality, chain-closure checks
9. **Output** — Artifact path + validation report

## Output Structure

agent-morph generates a Claude Code agent package with only:

```text
skills/       # Required
agents/       # As needed
hooks/        # As needed
scripts/      # As needed
MCP/          # As needed
README.md     # Required
```

The generated README guides you to place each directory where Claude Code can find it (e.g., `.claude/skills/`, `.claude/agents/`).

## Chain Closure

All generated components must be reachable from the main skill. No orphan components. Each component specifies:

- Who calls it
- What it calls
- What the input is
- Where the output goes

## Troubleshooting

### Input type misdetected

The model auto-detects input type (natural language / URL / local path). If misdetected, describe your need more clearly or provide a full path/URL.

### Generated package validation failed

This script only validates generated agent packages, not the plugin source.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate-agent-package.py <package-dir>
```

## Limitations

- Does not create new MCP servers
- Cannot guarantee all external URLs are accessible
- Does not generate arbitrary project structures outside allowed directories
- Does not treat output as a Claude Code plugin unless explicitly requested in design

## License

MIT
