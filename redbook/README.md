# redbook — 小红书 AI 图文一键工作流

一个 Claude Code Skill，说一句「今日小红书图文」，自动完成从 AI 日报选题 → PDF 解读 → HTML 图文生成 → 截图出图 → 配套文案的完整流程。

---

## 效果示例

> 见 [examples/小红书_AI勒索_图文.html](examples/小红书_AI勒索_图文.html)
>
> 基于「Claude 被用于生成勒索邮件」一文生成的 7 张白底卡片图文，包含封面大字、事件流程、对比卡、结尾追问等。

---

## 功能

- **自动选题**：调用 [AI HOT](https://aihot.virxact.com) 日报 API，筛选适合小红书传播的 3~5 篇文章
- **三种图文模板**：根据文章类型自动匹配
  - 📊 数据冲击型（融资额、准确率、排名对比）
  - 📖 故事叙事型（人物、事件、转折）
  - 💡 观点争议型（反常识结论、行业争议）
- **HTML 图文生成**：白底 750px 卡片，大标题 + 正文 + 彩色顶部装饰条，每张 ≤150 字
- **自动截图**：基于 Puppeteer，2x 清晰度，自动裁剪每张卡片输出 PNG
- **图片目录管理**：按 `YYYYMMDD_文章slug` 建子目录，不覆盖历史图片
- **小红书文案生成**：标题（≤20字）+ 正文（150~300字）+ 标签，可直接复制发布

---

## 快速开始

### 前置依赖

```bash
# Node.js 18+
node -v

# Puppeteer（截图用）
npm install puppeteer
```

### 安装 Skill

将本目录放到 Claude Code Skills 路径下即可：

```bash
~/.claude/skills/redbook/
├── SKILL.md
├── _meta.json
└── examples/
```

### 触发方式

在 Claude Code 中说：

```
今日小红书图文
```

或：

```
redbook
```

---

## 使用流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 自动拉取 AI 日报 | 推荐 3~5 篇适合小红书的文章 |
| 2 | 提供文章 PDF | 将文章 PDF 发给 Claude |
| 3 | 生成 HTML 图文 | 自动选模板，输出到 `~/Downloads/小红书_图文.html` |
| 4 | 预览确认 | 浏览器打开 HTML，确认无误后说「可以截图」 |
| 5 | 截图出图 | 自动生成 PNG，存入 `~/Downloads/小红书图片/YYYYMMDD_slug/` |
| 6 | 获取文案 | 输出可直接复制的标题 + 正文 + 标签 |

---

## 文件说明

```
redbook/
├── SKILL.md                    # Skill 主指令（Claude 读取执行）
├── _meta.json                  # Skill 元信息
├── README.md                   # 本文件
└── examples/
    ├── 小红书_AI勒索_图文.html   # 示例 HTML 图文（Claude 勒索案例）
    └── screenshot_cards.mjs    # Puppeteer 截图脚本
```

### screenshot_cards.mjs 用法

```bash
node screenshot_cards.mjs <html路径> <输出目录> <文章slug>

# 示例
node screenshot_cards.mjs ~/Downloads/小红书_图文.html ~/Downloads/小红书图片 claude-blackmail
```

---

## 依赖说明

| 依赖 | 用途 |
|------|------|
| [AI HOT API](https://aihot.virxact.com) | 获取每日 AI 精选资讯 |
| [Puppeteer](https://pptr.dev) | 无头浏览器截图 |
| Claude Code | 执行 Skill 的 AI 编程助手 |

---

## License

MIT
