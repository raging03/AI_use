---
name: skill-tester
description: 触发词：测试skill/skill测试/生成测试报告。对指定skill进行自动化测试并生成结构化测试报告，自动完成安装、运行测试、分析结果，输出标准化测试文档。
argument-hint: "<skill_url> <test_query> [evaluation_criteria]"
allowed-tools: Read Write Bash mcp__tavily__tavily-search mcp__tavily__tavily-extract
---

# Skill 测试器

## 概述

该skill用于对任意 skill 进行标准化测试，自动安装目标 skill、执行测试 query、分析输出结果，并生成包含测试人、测试时间、结论等完整字段的测试报告文档。

## 触发条件

当用户说出以下关键词时自动触发本 skill：
- `测试skill`
- `skill测试`
- `生成测试报告`
- `/test-skill`

触发后需要用户提供：
- skill 的下载地址（URL）
- 测试 query（支持多条，用换行或分号分隔）
- 评估标准（可选，用于判断输出质量）

## 使用方法

### 步骤1：解析用户输入

从用户消息中提取：
- `skill_url`：目标 skill 的 zip 下载地址
- `test_queries`：测试问题/指令列表（支持多条，用换行或分号分隔；若只有一条则作为单条处理）
- `evaluation_criteria`：评估标准（如无则使用默认标准：字数适中、语言准确、体裁符合）

**信息缺失时的澄清规则：**

- 若 `skill_url` 缺失：**必须停止**，询问用户提供下载地址，不得继续后续步骤
- 若 `test_queries` 缺失：**必须停止**，询问用户想测试哪些问题或指令
- 若 `evaluation_criteria` 缺失：**无需询问**，直接使用默认标准，告知用户即可
- 若多项信息缺失：**一次性**列出所有缺失项询问，避免多轮追问

### 步骤2：获取 Skill 元信息

**优先**执行脚本从 URL 预览并提取 skill 的元信息：

```bash
python3 ~/.claude/skills/skill-tester/scripts/get_skill_meta.py <skill_url>
```

脚本会输出 JSON 格式的元信息，包含：
- `name`：skill 名称
- `description`：skill 描述
- `install_path`：安装路径
- `skill_type`：skill 类型（Writing / Coding / Research / General 等）
- `downloads`：下载量（从 _meta.json 读取，若无则显示"未知"）

**若脚本不存在或执行失败**，改用 `mcp__tavily__tavily-extract` 直接抓取 URL 内容提取元信息，无法获取的字段填写"未知"。

### 步骤2.5：分析 Skill 环境依赖并告知用户

在安装前，**必须**通过已获取的 SKILL.md 内容（来自步骤2）分析该 skill 是否存在外部依赖，并在安装前向用户如实告知，**等待用户确认后才可继续安装**。

**分析维度：**

1. **外部 API 调用**：检测 SKILL.md 及脚本文件中是否包含以下特征：
   - 关键词：`api_key`、`API_KEY`、`Authorization`、`Bearer`、`token`、`secret`、`openai`、`anthropic`、`gemini`、`azure`、`aws`、`gcp` 等
   - HTTP 请求工具：`curl`、`requests`、`fetch`、`httpx`、`axios` 等
   - MCP 工具调用：`allowed-tools` 字段中包含 `mcp__` 前缀的工具

2. **沙盒 / 容器环境**：检测是否需要特殊运行环境：
   - 关键词：`docker`、`sandbox`、`container`、`virtualenv`、`conda`、`nix`、`wasm` 等

3. **本地服务依赖**：检测是否需要本地运行的服务：
   - 关键词：`localhost`、`127.0.0.1`、`port`、`server`、数据库连接串（`mysql`、`postgres`、`redis`、`mongodb`）等

4. **第三方包依赖**：检测是否需要额外安装包：
   - 关键词：`pip install`、`npm install`、`brew install`、`requirements.txt`、`package.json` 等

**分析完成后，向用户展示以下格式的告知信息：**

---

> ⚠️ **安装前环境依赖提示**
>
> 已分析 `{skill_name}` 的 SKILL.md，发现以下依赖情况：
>
> | 依赖类型 | 检测结果 | 说明 |
> |----------|----------|------|
> | 外部 API 调用 | ✅ 需要 / ❌ 不需要 | {具体说明，如：调用 OpenAI API，需配置 OPENAI_API_KEY} |
> | 沙盒/容器环境 | ✅ 需要 / ❌ 不需要 | {具体说明，如：需要 Docker 运行环境} |
> | 本地服务依赖 | ✅ 需要 / ❌ 不需要 | {具体说明，如：需要本地 Redis 服务} |
> | 第三方包依赖 | ✅ 需要 / ❌ 不需要 | {具体说明，如：需要 pip install requests} |
>
> **是否继续安装？**（若依赖未满足，skill 测试可能失败）
> - 回复"继续"或"是"：继续安装
> - 回复"取消"或"否"：终止本次测试

---

**等待用户明确回复后再执行步骤3**，不得在展示告知信息后自动继续安装。

**若 SKILL.md 内容在步骤2中未能获取**，则在此步骤填写"无法分析（元信息获取失败）"并仍然告知用户，由用户决定是否继续。

### 步骤3：安装目标 Skill

使用 skill-recommender 的安装脚本安装目标 skill：

```bash
python3 ~/.claude/skills/skill-recommender/scripts/install_skill.py <skill_name> <skill_url>
```

安装成功后确认安装路径。

### 步骤3.5：验证 Skill 是否安装成功

安装完成后，**必须**执行以下验证，确认 skill 已真实安装，才可进入测试阶段：

```bash
ls ~/.claude/skills/<skill_name>/SKILL.md 2>/dev/null && echo "INSTALLED" || echo "NOT_INSTALLED"
```

**验证结果处理规则：**

- **若输出 `INSTALLED`**：继续执行步骤4，进行真实 query 测试
- **若输出 `NOT_INSTALLED`**：**立即停止**，向用户发出以下提示，不得继续测试，不得伪造任何测试结果：

> ❌ Skill 安装验证失败：`{skill_name}` 未能成功安装到 `~/.claude/skills/` 目录。
>
> **请重新安装后再发起测试**，步骤如下：
> 1. 确认下载地址是否正确
> 2. 重新运行安装命令，或手动将 skill 目录放入 `~/.claude/skills/<skill_name>/`
> 3. 确认 `~/.claude/skills/<skill_name>/SKILL.md` 文件存在
> 4. 安装成功后，重新告诉我"测试skill"以开始测试

**严禁行为：** 安装验证失败时，不得：
- 用模拟输出代替真实 skill 调用结果
- 假装 skill 已安装并继续生成测试报告
- 跳过验证直接输出"测试结论"

### 步骤4：执行测试 Query

对 `test_queries` 中的每条 query，逐条调用已安装的 skill 执行，完整记录每条的输出结果。

通过 Skill 工具调用刚安装的 skill，传入每条 query 作为输入，不得跳过或合并执行。

**每条 query 执行前再次确认调用的是真实 skill**，若 Skill 工具返回错误或无响应，按"即时中断型错误"处理，不得用自行生成的内容替代 skill 输出。

### 步骤5：分析输出结果

对输出内容进行以下维度统计：
- **字数**：统计输出文本的字数（中文按字计，英文按词计）
- **体裁**：判断输出的文体类型（如：说明文、议论文、叙述文、技术文档、列表、代码等）
- **语言**：识别输出使用的语言（中文、英文、中英混合等）

### 步骤6：生成测试报告

按以下结构输出 Markdown 格式的测试报告：

---

## 📋 Skill 测试报告

### 一、测试 Skill 基本信息

| 字段 | 内容 |
|------|------|
| Skill 名称 | `{name}` |
| Skill 下载量 | {downloads} |
| 安装路径 | `{install_path}` |
| Skill 类型 | {skill_type} |
| 外部 API 依赖 | {有 / 无 / 未知，具体说明} |
| 沙盒/容器依赖 | {有 / 无 / 未知，具体说明} |

### 二、Skill 简介

{description}

### 三、测试 Query

> {test_query}

**评估标准：** {evaluation_criteria}

### 四、输出结果

每条 query 单独展示：

**Query 1：** {test_query_1}

{输出内容}

| 维度 | 结果 |
|------|------|
| 字数 | {word_count} 字/词 |
| 体裁 | {genre} |
| 语言 | {language} |

（多条 query 依次重复上述结构）

### 五、测试结论

{根据评估标准对输出结果进行综合评价，说明 skill 是否达到预期效果，以及优点和不足}

| 综合评级 | ⭐⭐⭐⭐ (4/5) |
|------|------|
| 评级说明 | {简要说明给出该评级的理由} |

### 六、测试信息

| 字段 | 内容 |
|------|------|
| 测试时间 | {YYYY-MM-DD HH:mm} |
| 测试人 | 江子怡 |

---

## 错误处理

错误分为两类处理方式：**即时中断型**（严重错误，需用户决策）和**记录型**（非致命错误，最终报告中注明）。

### 即时中断型错误（运行中实时提示）

遇到以下错误时，**立即暂停**，向用户说明错误原因并提供选项：

**下载 / 安装失败：**
> ❌ Skill 安装失败：{错误原因}
>
> 请选择如何继续：
> 1. 重新提供下载地址，重试安装
> 2. 跳过安装，仅基于 URL 内容进行有限测试
> 3. 终止本次测试

**Skill 调用失败（执行某条 query 时）：**
> ❌ Query {N} 执行失败：{错误原因}
>
> 请选择如何继续：
> 1. 修改该 query 后重试
> 2. 跳过该 query，继续测试剩余条目
> 3. 终止本次测试

### 记录型错误（在报告末尾统一注明）

以下错误不中断流程，在报告"七、异常记录"章节中汇总：

- **元信息缺失**：若 `_meta.json` 不存在，下载量填"未知"，并在异常记录中注明
- **字段解析失败**：某字段无法自动提取时，填"未知"并记录原因
- **脚本执行警告**：非致命的脚本警告信息

报告末尾新增章节：

### 七、异常记录

| 异常类型 | 详情 |
|----------|------|
| {异常类型} | {具体说明} |

（若无异常，该章节填写"无"）

## 重要提示

- 测试人固定为"江子怡"
- 测试时间自动使用当前系统时间
- 下载量从 skill 包内的 `_meta.json` 文件读取，若不存在则填"未知"
- Skill 类型根据 SKILL.md 内容自动判断：含 writing/文章/写作 关键词归类为 Writing；含 code/编程/开发 归类为 Coding；含 research/分析/报告 归类为 Research；其他归类为 General
- 安装完成后必须实际调用该 skill 执行测试，不能伪造输出
- 报告使用 Markdown 格式输出，结构清晰、字段完整
