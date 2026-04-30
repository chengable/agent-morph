# agent-morph

把用户需求或资源自动转换成链式闭环的 Claude Code 智能体包。

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

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/detect-input-type.py '<输入>'
```

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
