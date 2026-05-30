# ChemVision AI 化学家

基于 ≤35B 本地模型（Ollama + Qwen3.6-35B-A3B）驱动的化学工具调用 Skill。
通过 PubChem 和 OPSIN 真实化学数据库查询，减少 LLM 化学幻觉。

## 触发条件

当用户提出以下类型的问题时，使用此技能：
- 查询化学名称对应的分子结构（SMILES、分子式、分子量）
- 解析 SMILES 字符串获取化学信息
- 查询化学品安全信息和危险标识
- 推测化学反应方程式和条件
- 提供化学结构图片需要识别

## 使用方式

通过 HTTP API 调用本地化学工具服务（`http://localhost:8899`）。

### 工具 1：name_to_structure（化学名称解析）

将化学名称转换为分子结构信息。支持中文名、英文名、IUPAC名、俗名。

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "name_to_structure", "arguments": {"name": "苯甲酸"}}'
```

返回示例：
```json
{
  "success": true,
  "query": "苯甲酸",
  "smiles": "c1ccc(cc1)C(=O)O",
  "molecular_formula": "C7H6O2",
  "molecular_weight": 122.12,
  "iupac_name": "benzoic acid",
  "cid": 244,
  "source": "pubchem"
}
```

### 工具 2：inspect_smiles（SMILES 信息查询）

查询 SMILES 字符串对应的化学信息。

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "inspect_smiles", "arguments": {"smiles": "CCO"}}'
```

### 工具 3：safety_info（化学品安全信息）

查询化学品的 GHS 危险标识、危害分类、安全提示。

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "safety_info", "arguments": {"query": "苯"}}'
```

### 工具 4：predict_reaction（化学反应推测）

推测化学反应的产物、方程式和反应条件。

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "predict_reaction", "arguments": {"reactants": "乙酸和乙醇", "conditions": "催化剂硫酸，加热"}}'
```

### 工具 5：ocr_chemistry（化学结构图片识别）

从化学结构图片中识别化合物（需 base64 编码图片）。

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "ocr_chemistry", "arguments": {"image_base64": "<base64数据>"}}'
```

### Agent 对话接口（自动路由工具）

也可以直接使用 Agent 对话接口，让 LLM 自动决定调用哪个工具：

```bash
curl -X POST http://localhost:8899/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "苯甲酸的分子结构是什么？"}'
```

## 前置要求

1. Python 3.10+
2. Ollama 已安装并运行，且已下载 qwen3.6-35b-a3b 模型
3. 化学工具服务已启动：`python -m chemskill.server`（端口 8899）

## 注意事项

- 所有化学数据来自 PubChem 真实数据库，非 LLM 推测
- 服务运行在本地，化学数据不出机
- 如果服务未启动，工具调用会返回连接错误
