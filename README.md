# ChemVision Agent Skill — AI 化学家智能体

> 基于 ≤35B 本地小模型（Ollama + Qwen3.6-35B-A3B）驱动化学工具调用的 Agent Skill

## 项目简介

ChemVision Skill 是一个**本地运行**的化学智能体，通过 function calling 机制调用真实的化学数据库（PubChem、OPSIN），实现化学名称解析、结构查询、安全信息查询、反应推测、图片识别等能力。

**核心创新**：LLM 不再"凭记忆"生成化学数据，而是通过工具调用验证事实，**大幅减少化学幻觉**。

### 架构图

```
用户提问
    ↓
┌─────────────────────────────┐
│  Ollama + Qwen3.6-35B-A3B  │ ← Agent 大脑 (≤35B, 本地运行)
│  Function Calling 决策       │
└──────┬──────────────────────┘
       ↓ tool_calls
┌──────────────────────────────────────────┐
│  name_to_structure │ inspect_smiles      │ ← 5 个化学工具
│  safety_info       │ predict_reaction    │
│  ocr_chemistry                            │
└──────┬───────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│  PubChem API  │  OPSIN API  │  LLM 推理  │ ← 真实数据源
└──────────────────────────────────────────┘
       ↓
   结构化结果 → LLM 汇总 → 自然语言回答
```

### 5 个化学工具

| 工具 | 功能 | 数据源 |
|------|------|--------|
| `name_to_structure` | 化学名称→SMILES/分子式/分子量 | PubChem + OPSIN |
| `inspect_smiles` | SMILES→化学信息查询 | PubChem |
| `safety_info` | 化学品安全信息（GHS、危险标识） | PubChem Safety |
| `predict_reaction` | 反应方程式推测与条件建议 | LLM 推理 |
| `ocr_chemistry` | 化学结构图片识别 | 多模态 LLM |

## 快速开始

### 前置要求

1. **Python 3.10+**
2. **Ollama** 已安装 ([ollama.ai](https://ollama.ai))
3. **Qwen3.6-35B-A3B** 模型已下载

### 安装

```bash
cd chemvision-skill

# 安装依赖
pip install -r requirements.txt

# 确认 Ollama 已启动并下载模型
ollama pull qwen3.6-35b-a3b
```

### 运行

#### 方式 1: CLI 交互式（推荐演示）

```bash
python -m demo.demo_cli
```

示例对话：
```
🧑 你: 苯甲酸的结构是什么？

🤖 Agent 思考中...

📋 工具调用记录：
  1. ✅ name_to_structure({"name": "苯甲酸"})

🔬 Agent:
苯甲酸（Benzoic acid）的分子结构信息如下：

- SMILES: c1ccc(cc1)C(=O)O
- 分子式: C7H6O2
- 分子量: 122.12 g/mol
- IUPAC 名称: benzoic acid
- PubChem CID: 244
```

#### 方式 2: HTTP API 服务

```bash
# 启动服务
python -m chemskill.server

# 调用 API
curl -X POST http://localhost:8899/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "乙醇的 SMILES 和分子量"}'
```

#### 方式 3: 直接工具调用

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "name_to_structure", "arguments": {"name": "ethanol"}}'
```

---

## 使用 QwenPaw 本地测试

[QwenPaw](https://modelscope.cn/brand/view/ai_pc) 是魔搭社区的本地 Agent 桌面助手，可直接调用本地 Skill 进行测试。

### 前置准备

1. 启动 ChemVision Skill HTTP 服务：
```bash
cd chemvision-skill
python -m chemskill.server
# 服务运行在 http://localhost:8899
```

2. 确认 Ollama 已运行且模型已就绪：
```bash
ollama list            # 查看已下载模型
ollama ps              # 查看正在运行的模型
```

### 测试方式 A：通过 API 直接对话（无需 QwenPaw）

最简单的方式，验证 Agent + 工具链是否正常工作：

```bash
# 化学名称解析
curl -X POST http://localhost:8899/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "苯甲酸的分子结构是什么？"}'

# SMILES 查询
curl -X POST http://localhost:8899/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "CC(=O)Oc1ccccc1C(=O)O 是什么物质？"}'

# 安全信息
curl -X POST http://localhost:8899/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "苯有哪些安全风险？"}'

# 反应推测
curl -X POST http://localhost:8899/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "乙酸和乙醇反应生成什么？"}'
```

### 测试方式 B：通过 QwenPaw 调用 Skill

QwenPaw 会读取 Skill 的 OpenAPI Schema（`skill_manifest/tools_schema.json`），自动注册工具后进行调用。

**步骤：**

1. 在 QwenPaw 中添加 Skill，指向 `http://localhost:8899`
2. QwenPaw 会自动发现以下 API 端点：
   - `POST /api/chat` — Agent 对话（推荐）
   - `POST /api/tools/call` — 直接工具调用
   - `GET  /api/tools/list` — 工具列表
   - `GET  /api/health` — 健康检查

3. 在 QwenPaw 对话框中输入化学问题，观察：
   - Agent 是否正确调用了工具（看 tool_calls 记录）
   - 返回的化学数据是否来自 PubChem（而非 LLM 幻觉）
   - 中文名是否正确翻译并解析

### 测试方式 C：使用 OpenAPI Schema 注册

将 `skill_manifest/tools_schema.json` 导入 QwenPaw 的 Skill 管理界面，或直接让 QwenPaw 访问：

```
http://localhost:8899/openapi.json
```

FastAPI 自动生成的 OpenAPI 文档地址：
```
http://localhost:8899/docs     # Swagger UI（可视化测试）
http://localhost:8899/redoc    # ReDoc（文档查看）
```

### 验证清单

| 测试项 | 输入 | 预期结果 |
|--------|------|----------|
| 化学名称解析 | "苯甲酸的结构" | 调用 `name_to_structure`，返回 SMILES、C7H6O2 |
| SMILES 查询 | "CCO 是什么" | 调用 `inspect_smiles`，返回乙醇信息 |
| 中文名解析 | "乙醇的分子式" | 自动翻译 → PubChem 查询，返回 C2H6O |
| 安全查询 | "苯的危险标识" | 调用 `safety_info`，返回 GHS 数据 |
| 反应推测 | "乙酸和乙醇反应" | 调用 `predict_reaction`，返回酯化反应 |
| 多轮组合 | "阿司匹林的安全信息" | 先解析名称获取 CID，再查安全数据 |
| 错误处理 | "不存在的化学物质xyz123" | 优雅返回错误信息，不崩溃 |

---

## 技术亮点

1. **减少化学幻觉**：LLM 通过 function calling 调用 PubChem 真实数据库，而非凭记忆生成
2. **双源容错解析**：PubChem + OPSIN 双数据源，主源失败自动切换备用源
3. **中文智能翻译**：内置高频中文化学名词典，无需 LLM 即可快速映射
4. **多轮工具组合**：Agent 可串联多个工具完成复杂查询
5. **本地运行**：基于 Ollama，所有推理在本地完成，敏感化学数据不出机
6. **OpenAPI 规范**：完整的 API Schema，可被 QwenPaw / Trae 等任何 Agent 框架调用

## 适用场景

- **化学教育**：学生查询化学名称、结构、安全信息
- **科研辅助**：快速检索化合物性质，验证结构式
- **药企研发**：药物分子结构查询与安全数据
- **实验安全**：化学品 GHS 标识查询与风险提示

## 项目结构

```
chemvision-skill/
├── chemskill/              # 核心包
│   ├── agent.py            # Agent 核心（Ollama function calling）
│   ├── server.py           # FastAPI 服务端
│   ├── config.py           # 配置管理
│   ├── tools/              # 5 个化学工具
│   ├── prompts/            # 系统提示词
│   └── utils/              # PubChem/OPSIN 客户端
├── skill_manifest/         # ModelScope Skill 清单 + OpenAPI Schema
├── demo/                   # 演示脚本
└── docs/                   # 文档
```

## 比赛信息

本项目参加 **AI PC Agent Skills 征文活动**（Intel + 魔搭社区）。

| 标签 | 值 |
|------|-----|
| 技术栈 | Python + FastAPI + Ollama + Qwen3.6-35B-A3B |
| Agent 框架 | 自研 function calling router |
| 化学数据源 | PubChem REST API + OPSIN |
| 运行环境 | 纯本地 (Localhost) |
| Skill 标签 | AIPC, chemistry, agent, tool-calling |

## License

MIT
