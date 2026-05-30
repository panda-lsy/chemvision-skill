# ChemVision Agent Skill — AI 化学家智能体

> 基于 ≤35B 本地小模型（Ollama + Qwen3.6-35B-A3B）驱动化学工具调用的 Agent Skill

## 快速开始

### 1. 启动化学工具服务

```bash
cd chemvision-skill
pip install -r requirements.txt
python -m chemskill.server
# 服务运行在 http://localhost:8899
```

### 2. 安装 Skill 到 QwenPaw

**方式 A：直接复制（推荐）**

```powershell
# Windows PowerShell
Copy-Item -Recurse skill_pool\chemvision $env:USERPROFILE\.qwenpaw\skill_pool\

# 或复制到工作区
Copy-Item -Recurse skill_workspaces\default\skills\chemvision $env:USERPROFILE\.qwenpaw\workspaces\default\skills\
```

```bash
# macOS / Linux
cp -r skill_pool/chemvision ~/.qwenpaw/skill_pool/

# 或复制到工作区
cp -r skill_workspaces/default/skills/chemvision ~/.qwenpaw/workspaces/default/skills/
```

复制后重启 QwenPaw 即可。

**方式 B：手动操作**

1. 打开 `~/.qwenpaw/skill_pool/` 目录
2. 将 `skill_pool/chemvision/` 文件夹整个复制进去
3. 确保 `skill.json` 中包含 `"chemvision"` 条目
4. 重启 QwenPaw

### 3. 在 QwenPaw 中测试

在 QwenPaw 对话框中输入化学问题，例如：

- "苯甲酸的分子结构是什么？"
- "CC(=O)Oc1ccccc1C(=O)O 是什么物质？"
- "苯的安全风险有哪些？"
- "乙酸和乙醇反应生成什么？"

QwenPaw 会自动识别为化学相关问题，调用 ChemVision Skill。

## 架构

```
用户提问
    ↓
QwenPaw + Qwen3.6-35B-A3B（本地 ≤35B 模型）
    ↓ 读取 SKILL.md，决定调用工具
    ↓
http://localhost:8899/api/tools/call
    ↓
┌──────────────────────────────────────────┐
│  name_to_structure │ inspect_smiles      │ ← 5 个化学工具
│  safety_info       │ predict_reaction    │
│  ocr_chemistry                            │
└──────┬───────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│  PubChem API  │  OPSIN API  │  LLM 推理  │ ← 真实数据源
└──────────────────────────────────────────┘
```

## 5 个化学工具

| 工具 | 功能 | 数据源 |
|------|------|--------|
| `name_to_structure` | 化学名称→SMILES/分子式/分子量 | PubChem + OPSIN |
| `inspect_smiles` | SMILES→化学信息查询 | PubChem |
| `safety_info` | 化学品安全信息（GHS、危险标识） | PubChem Safety |
| `predict_reaction` | 反应方程式推测与条件建议 | LLM 推理 |
| `ocr_chemistry` | 化学结构图片识别 | 多模态 LLM |

## 直接 API 测试（不通过 QwenPaw）

```bash
# 健康检查
curl http://localhost:8899/api/health

# Agent 对话
curl -X POST http://localhost:8899/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "乙醇的 SMILES 和分子量"}'

# 直接工具调用
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "name_to_structure", "arguments": {"name": "ethanol"}}'

# Swagger UI（可视化测试）
# 浏览器访问 http://localhost:8899/docs
```

## 项目结构

```
chemvision-skill/
├── skill_pool/             # QwenPaw 技能池格式
│   ├── skill.json          # 池清单
│   └── chemvision/
│       └── SKILL.md        # 技能定义（QwenPaw 读取此文件）
├── skill_workspaces/       # QwenPaw 工作区格式
│   └── default/
│       ├── skill.json
│       └── skills/chemvision/SKILL.md
├── chemskill/              # Python 核心代码
│   ├── agent.py            # Agent 核心（Ollama function calling）
│   ├── server.py           # FastAPI 服务端
│   ├── tools/              # 5 个化学工具
│   ├── prompts/            # 系统提示词
│   └── utils/              # PubChem/OPSIN 客户端
├── skill_manifest/         # ModelScope 发布用清单（备用）
├── requirements.txt
└── README.md
```

## 比赛信息

本项目参加 **AI PC Agent Skills 征文活动**（Intel + 魔搭社区）。

| 标签 | 值 |
|------|-----|
| 技术栈 | Python + FastAPI + Ollama + Qwen3.6-35B-A3B |
| Agent 框架 | QwenPaw + 自研 function calling router |
| 化学数据源 | PubChem REST API + OPSIN |
| 运行环境 | 纯本地 (Localhost) |
| Skill 标签 | AIPC, chemistry, agent, tool-calling |

## License

MIT
