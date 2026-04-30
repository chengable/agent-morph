# Agent Morph 确认设计

## 1. 目标

`agent-morph` 是一个 Claude Code 插件，用于把用户的一句话需求或外部资料，转换成一个完整的 Claude Code 智能体包。

本文中的“智能体”指一个完整的 Claude Code 工作系统，不只是 Claude Code 的 subagent。生成物可以包含 skills、agents、MCP 配置、hooks、scripts 和 README 文档。

## 2. 范围

### agent-morph 自身是一个插件

agent-morph 插件自身提供一个主入口 skill，并包含若干内部 subagents、scripts、hooks，用于设计、构建、验证目标智能体包。

### agent-morph 的输出是智能体包

agent-morph 的生成物默认不等同于插件。它是一个 Claude Code 智能体包，目录结构被强约束为：

```text
skills/
agents/
MCP/
hooks/
scripts/
README.md
```

如果某个目标场景适合以插件方式安装，生成的 README 可以说明如何放置或安装这些组件，但 agent-morph 不应默认把每个输出都视为插件。

## 3. 硬约束

### 3.1 生成物必须链式闭环

生成出来的任何组件都不能孤立存在。

每个组件都必须能从主 skill 工作流中被触达：

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

组件可达性规则：

| 组件 | 必须被谁引用 |
|---|---|
| 子 skill | 主 skill 或某个 agent |
| Agent | 主 skill 或其他 agent |
| Script | Skill、agent 或 hook |
| MCP 配置 | 明确说明使用时机的 skill 或 agent |
| Hook | 明确的 Claude Code 事件和工作流目的 |
| README | 必须说明组件链路 |

禁止示例：

```text
skills/random-helper/SKILL.md   # 没有调用方
scripts/parse.py                # 没有调用方
agents/extra-reviewer.md        # 从未被分派
MCP/.mcp.json                   # 没有工作流使用说明
```

只要存在孤立组件，验证直接失败。

### 3.2 构建和验证必须基于 superpowers 流程

`agent-builder` 和 `agent-validator` 必须把 superpowers 的开发纪律作为默认实现和验证基线：

- 大量生成文件前，先写计划或遵循已有计划
- 按步骤执行计划
- 完成前必须验证
- 适用时使用 review / validation 流程
- 不跳过验证门禁

### 3.3 组件定义必须遵循 plugin-dev 最佳实践

生成 skills、agents、hooks、MCP 配置或 README 时，agent-morph 必须遵循 plugin-dev 的结构和质量规则：

- skill 使用 `skills/<name>/SKILL.md`
- skill 需要强触发描述，且使用第三人称描述触发场景
- skill 正文写给 Claude 执行，不是写给用户看的说明书
- agent 需要清楚的 frontmatter、触发示例、工具、职责边界和输出格式
- hook 使用合法的 `hooks/hooks.json` 结构
- MCP 只引用已有 MCP server；agent-morph 不创造新的 MCP server
- 生成文档必须说明安装、使用、依赖和组件链路

## 4. agent-morph 插件自身组件

### 4.1 插件清单

```text
.claude-plugin/plugin.json
```

用途：

- 标识插件名为 `agent-morph`
- 定义版本、描述、作者、关键词
- 尽量依赖默认组件自动发现机制

### 4.2 主 skill

```text
skills/agent-morph/SKILL.md
```

用途：

- 唯一用户入口
- 编排完整工作流
- 不直接做重活
- 分派内部 agents 完成资源读取、调研、设计、构建和验证

预期用户输入：

1. 自然语言需求
2. 开源项目 URL
3. 本地代码路径
4. Web URL
5. 文件 URL
6. 本地文件路径

主流程：

1. 使用 `scripts/detect-input-type.py` 判断输入类型。
2. 分派 `resource-reader` 读取和总结原始资料。
3. 围绕三个问题澄清目标智能体设计：
   - 最终目标和预期输出
   - 需要的数据来源和数据处理过程
   - 预期用户输入形态
4. 如仍有不确定点，向用户提问。每组选项都必须包含“你自动调研”选项。
5. 澄清完成后，分派 `researcher` 调研不确定点。
6. 分派 `agent-architect` 产出最终确认设计。
7. 请求用户最终确认。
8. 写入 `<english-agent-name>-confirm-design.md`。
9. 分派 `agent-builder` 基于 superpowers 和 plugin-dev 最佳实践生成目标智能体包。
10. 分派 `agent-validator` 验证生成物。
11. 返回最终路径、验证结果和使用说明。

### 4.3 resource-reader agent

```text
agents/resource-reader.md
```

用途：

- 读取并归一化用户提供的原始资料
- 识别可复用的思路、流程、数据源和约束

输入：

- 用户原始输入
- 已判断出的输入类型
- 可选的本地路径或 URL

不同输入类型的处理方式：

| 输入类型 | 处理方式 |
|---|---|
| 自然语言 | 提取显性和隐性需求 |
| GitHub / 开源项目 URL | 建议 clone / read 策略；可用时检查项目结构和文档 |
| 本地代码路径 | 探索结构并读取关键文件 |
| Web URL | 使用可用网页工具抓取可读内容 |
| 文件 URL | 使用合适工具获取 / 读取文件内容 |
| 本地文件路径 | 根据文件类型读取或转换内容 |

输出：

```text
- 输入类型
- 原始资源位置
- 资源摘要
- 关键能力
- 可复用模式
- 缺失信息
- 建议调研问题
```

### 4.4 researcher agent

```text
agents/researcher.md
```

用途：

- 在需求澄清后，调研不确定的设计点

调研主题：

- 现有开源项目
- 现有 MCP server
- 可复用库 / 工具
- 目标领域最佳实践
- 特殊输出格式工具
- 数据获取方案
- 数据处理方法
- Claude Code skills / agents / hooks / MCP 约束

输出：

```text
- 调研问题
- 发现的选项
- 推荐选项
- 取舍理由
- 可复用工具 / MCP / 库
- 对目标智能体设计的影响
```

### 4.5 agent-architect agent

```text
agents/agent-architect.md
```

用途：

- 把澄清后的需求和调研结果转换为目标智能体包设计

职责：

- 定义主 skill
- 定义必要的子 skills
- 定义必要的 agents
- 仅当存在合适的现成 MCP 时，定义 MCP 使用方式
- 定义必要 hooks
- 为固定流程或结构化处理定义 scripts
- 定义用户输入、数据来源、数据处理过程和最终输出
- 产出组件链路，确保每个组件都有调用方和明确用途

必须输出的章节：

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

### 4.6 agent-builder agent

```text
agents/agent-builder.md
```

用途：

- 根据 `<english-agent-name>-confirm-design.md` 生成目标智能体包

强制行为：

- 大量生成文件前，使用 superpowers 的计划 / 执行纪律
- 遵循 plugin-dev 对 skill / agent / hook / MCP 的最佳实践
- 只生成确认设计中出现的组件
- 拒绝或修正会产生孤立组件的设计元素
- 每个生成组件都必须明确自己在链路中的调用方 / 被调用方关系

生成物结构：

```text
skills/
  <main-skill>/SKILL.md
  <sub-skill>/SKILL.md
agents/
  <agent-name>.md
MCP/
  .mcp.json
hooks/
  hooks.json
  scripts/...
scripts/
  ...
README.md
```

除 `README.md` 和主 `skills/` 入口总是必须存在外，其他目录只在确认设计需要时创建。

### 4.7 agent-validator agent

```text
agents/agent-validator.md
```

用途：

- 验证生成的目标智能体包

强制行为：

- 使用 superpowers 的 completion 前验证纪律
- 使用 plugin-dev 的组件定义质量规则
- 运行或调用 `scripts/validate-agent-package.py` 做结构校验
- 检查组件链路可达性
- 如果发现任何孤立组件，验证失败

验证清单：

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

输出：

```text
- 通过项
- 失败项
- 孤立组件，如有
- 必须修复项
- 建议优化项
- 最终可交付状态：pass/fail
```

### 4.8 detect-input-type script

```text
scripts/detect-input-type.py
```

用途：

- 在模型解释前，使用确定性逻辑判断用户输入类型

输入：

```text
用户原始参数字符串
```

输出 JSON：

```json
{
  "type": "github_repo | web_url | file_url | local_path | local_file | natural_language",
  "value": "...",
  "confidence": 0.92
}
```

被谁使用：

- `skills/agent-morph/SKILL.md`
- `agents/resource-reader.md`

### 4.9 validate-agent-package script

```text
scripts/validate-agent-package.py
```

用途：

- 对生成的智能体包做确定性结构校验

检查项：

- `README.md` 存在
- `skills/` 存在
- 至少存在一个主 skill
- 根目录只包含允许项
- skill 和 agent markdown 文件存在 frontmatter
- 如存在 `hooks/hooks.json`，必须能解析
- 如存在 `MCP/.mcp.json`，必须能解析
- 组件链路元数据或 README 必须引用每个组件

被谁使用：

- `agents/agent-validator.md`

### 4.10 Stop guard hook

```text
hooks/hooks.json
hooks/scripts/stop-guard.py
```

用途：

- 防止 agent-morph 在必需流程完成前提前停止

触发：

- Claude Code `Stop` 事件

默认阻止行为：

- 在 agent-morph 工作流激活期间，最多阻止 2 次过早停止

完成条件：

- 确认设计文件已存在
- 目标智能体包已生成
- 结构验证已执行
- 验证报告已生成
- 已返回最终路径和使用说明

### 4.11 README

```text
README.md
```

用途：

- 说明 agent-morph 的安装、依赖和使用方式

必需章节：

1. 概览
2. 前置依赖
   - superpowers 插件
   - plugin-dev 插件
3. 安装方式
4. 使用方式
5. 支持的输入类型
6. 工作流
7. 生成物目录结构
8. 组件链式闭环规则
9. 验证行为
10. 限制
11. 故障排查

## 5. 目标智能体包规则

生成的目标智能体包必须遵循此根目录结构：

```text
skills/
agents/
MCP/
hooks/
scripts/
README.md
```

规则：

- `skills/` 和 `README.md` 必须存在
- 必须存在一个主 skill
- 其他目录只在需要时创建
- 所有生成组件都必须被主流程使用
- 生成物目录中使用大写 `MCP/`，这是本项目对目标智能体包的约定
- agent-morph 自身如果将来需要 MCP，仍应遵循 Claude Code 插件标准的 `.mcp.json` 位置

## 6. 工作流细节

### 阶段 1：输入接收

- 接收用户参数
- 判断输入类型
- 分派 resource-reader
- 产出归一化资源摘要

### 阶段 2：需求澄清

澄清：

1. 目标和最终输出
2. 数据需求、数据来源和处理路径
3. 预期用户输入

如有不确定点，提出聚焦问题。每组选项都必须包含“你自动调研”。

### 阶段 3：调研

- 分派一个或多个 researcher 任务
- 调研不确定的工具、MCP、库、领域方法和输出格式
- 返回带取舍理由的推荐方案

### 阶段 4：最终设计

- 分派 agent-architect
- 产出最终需求、技术方案、实现逻辑、目录结构和组件链路
- 请求用户最终确认
- 写入 `<english-agent-name>-confirm-design.md`

### 阶段 5：构建

- 分派 agent-builder
- 遵循 superpowers 实现纪律
- 遵循 plugin-dev 组件最佳实践
- 生成目标智能体包

### 阶段 6：验证

- 分派 agent-validator
- 执行确定性结构校验
- 验证链式闭环
- 验证 plugin-dev 质量标准
- 返回 pass/fail 报告

## 7. 成功标准

agent-morph 成功的标准：

1. 用户可以用自然语言需求、URL、项目路径或文件路径调用主 skill。
2. agent-morph 在构建前会澄清目标、数据、流程和输入形态。
3. agent-morph 在最终设计前会调研不确定点。
4. agent-morph 在生成前会写入确认设计文档。
5. agent-morph 会生成只包含允许目录的目标智能体包。
6. 每个生成组件都能从主 skill 链路触达。
7. 生成物通过确定性结构校验。
8. 生成物符合 plugin-dev 质量约定。
9. 构建和验证遵循 superpowers 验证纪律。
10. README 说明如何使用、安装和理解生成物。

## 8. 非目标

- agent-morph 不创造新的 MCP server。
- agent-morph 不保证所有外部 URL 都可访问。
- agent-morph 不生成允许目录以外的任意项目结构。
- 除非确认设计明确要求插件化打包，否则 agent-morph 不把每个生成物都视为 Claude Code 插件。
- agent-morph 不允许孤立 helper 文件、未使用脚本或断开的 skills。
