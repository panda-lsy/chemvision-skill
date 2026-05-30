# ChemVision Agent Skill — AI 化学家智能体

> **AI PC Agent Skills 征文活动** 参赛作品
>
> 用 ≤35B 本地小模型驱动化学工具调用，通过 PubChem 真实数据库消除 LLM 化学幻觉

## 项目简介

ChemVision Skill 是一个**本地运行**的化学数据查询服务，供 Agent（QwenPaw / Trae）调用。核心创新：

**LLM 不再"凭记忆"生成化学数据，而是通过调用 PubChem / OPSIN 真实化学数据库来验证事实，大幅减少化学幻觉。**

### 架构

```
用户: "苯甲酸的分子结构是什么？"
    ↓
QwenPaw + Qwen3.6-35B-A3B（本地 ≤35B 模型）
    ↓ 读取 SKILL.md，识别为化学问题
    ↓ 调用 POST /api/tools/call
┌───────────────────────────────────────┐
│  name_to_structure → PubChem + OPSIN  │  化学数据查询服务
│  inspect_smiles    → PubChem          │  （纯数据，无 LLM 依赖）
│  safety_info       → PubChem Safety   │
│  predict_reaction  → PubChem          │
└──────────┬────────────────────────────┘
           ↓ JSON 结果 + svg_url
    Agent 格式化回答 + 打开分子结构图截图
    ↓
send_file_to_user → 用户看到化学数据 + 分子结构图
```

### 4 个化学工具

| 工具                  | 功能                                     | 数据源          |
| --------------------- | ---------------------------------------- | --------------- |
| `name_to_structure` | 化学名称→SMILES/分子式/分子量 + 结构图  | PubChem + OPSIN |
| `inspect_smiles`    | SMILES→化学信息查询                     | PubChem         |
| `safety_info`       | 化学品安全信息（GHS、危险标识）          | PubChem Safety  |
| `predict_reaction`  | 反应物化学数据查询（Agent 自行推测反应） | PubChem         |

### 渲染能力

| 端点                      | 功能                                   |
| ------------------------- | -------------------------------------- |
| `GET /api/svg/{smiles}` | 分子结构图（smiles-drawer.js）         |
| `GET /api/formula/{eq}` | 化学方程式（自动下标、箭头、条件标注） |

## 快速开始

### 前置要求

1. **Python 3.10+**
2. **QwenPaw** 或 **Trae**（Agent 框架）

### 安装

```bash
cd chemvision-skill
pip install -r requirements.txt
```

### 启动服务

```bash
python manage.py start
# 输出: {"status": "started", "pid": 12345, "port": 8899}
```

### 管理服务

```bash
python manage.py status    # 查看状态
python manage.py stop      # 安全停止（不影响 QwenPaw）
python manage.py restart   # 重启
```

### 在 QwenPaw 中使用

1. 将 `chemvision-skill.zip` 导入 QwenPaw
2. 对话框输入：`苯甲酸的分子结构是什么？`

## 测试验证

### 健康检查

```bash
curl http://localhost:8899/api/health
# {"status":"ok","tools_count":4,"tools":["name_to_structure","inspect_smiles","safety_info","predict_reaction"]}
```

### 化学名称解析

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"name_to_structure","arguments":{"name":"苯甲酸"}}'
```

返回 SMILES、分子式、分子量、`svg_url`（分子结构图链接）。

### 安全信息查询

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name":"safety_info","arguments":{"query":"benzene"}}'
```

返回 GHS 危险标识、危害声明、防护措施等 42+ 字段。

### 化学方程式渲染

```
浏览器打开: http://localhost:8899/api/formula/CH3COOH+C2H5OH<=>[浓硫酸][加热]CH3COOC2H5+H2O
```

渲染效果：

```
                浓硫酸
CH₃COOH + C₂H₅OH  ⇌  CH₃COOC₂H₅ + H₂O
                 加热
```

## 设计理念

### 为什么选择"化学"场景？

化学是 LLM 幻觉最严重的领域之一。SMILES、分子式、分子量等数据必须精确——一个数字错误就是完全不同的物质。传统 LLM 凭记忆生成的化学数据经常出错。

**我们的解决方案**：Agent 的"大脑"负责理解用户意图和组织回答，但具体化学数据全部来自 PubChem 真实数据库。这就是 **Agentic AI 的核心价值** —— LLM 负责推理，工具负责事实。

### 工程亮点

- **零 LLM 依赖**：工具服务本身不调用任何模型，纯数据查询
- **双源容错**：PubChem + OPSIN 双数据源，主源失败自动切换
- **中文智能映射**：内置高频中文化学名词典（乙醇→ethanol），无需 LLM 翻译
- **安全进程管理**：`manage.py` 用 PID 文件精确追踪，不影响 QwenPaw 进程
- **纯 HTML 渲染**：分子结构图（smiles-drawer.js）+ 化学方程式（CSS 下标/箭头），无外部依赖

## 项目结构

```
chemvision-skill/
├── SKILL.md              ← QwenPaw 读取的技能定义
├── manage.py             ← 服务生命周期管理
├── chemskill/
│   ├── server.py         ← FastAPI 工具服务（4 端点）
│   ├── config.py         ← 配置
│   ├── tools/            ← 4 个化学工具
│   ├── utils/            ← PubChem + OPSIN 客户端
│   └── static/
│       └── smiles-drawer.js  ← 分子结构渲染引擎
├── requirements.txt      ← 仅 4 个依赖（fastapi, uvicorn, httpx, pydantic）
└── pyproject.toml
```

## License

MIT
