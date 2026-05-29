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
# 克隆项目
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

## 运行测试

```bash
# 单元测试（无需 Ollama）
pytest tests/test_tools.py -v

# Agent 测试（无需 Ollama，使用 mock）
pytest tests/test_agent.py -v

# 端到端测试（需要 Ollama + 网络）
pytest tests/test_e2e.py -v
```

## 技术亮点

1. **减少化学幻觉**：LLM 通过 function calling 调用 PubChem 真实数据库，而非凭记忆生成
2. **双源容错解析**：PubChem + OPSIN 双数据源，主源失败自动切换备用源
3. **中文智能翻译**：内置高频中文化学名词典，无需 LLM 即可快速映射
4. **多轮工具组合**：Agent 可串联多个工具完成复杂查询（先解析名称→再查安全信息）
5. **本地运行**：基于 Ollama，所有推理在本地完成，敏感化学数据不出机
6. **OpenAPI 规范**：完整的 API Schema，可被任何 Agent 框架调用

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
├── skill_manifest/         # ModelScope Skill 清单
├── tests/                  # 测试
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
