---
name: chemvision
description: Use this skill when the user asks about chemistry — chemical names, molecular structures (SMILES), molecular formulas, molecular weights, safety information (GHS hazards), or chemical reaction predictions. Supports Chinese and English chemical names, IUPAC names, and common names. Calls PubChem and OPSIN real chemistry databases via local API to reduce LLM hallucinations.
metadata:
  skill_version: "1.0.0"
  tags: ["AIPC", "chemistry", "agent", "tool-calling", "pubchem"]
---

# ChemVision AI 化学家

基于 ≤35B 本地模型（Ollama + Qwen3.6-35B-A3B）驱动的化学工具调用 Skill。
通过 PubChem 和 OPSIN 真实化学数据库查询，减少 LLM 化学幻觉。

## When to Use

Use this skill when the user:
- Asks about a chemical compound's structure, SMILES, molecular formula, or molecular weight
- Provides a chemical name (Chinese or English) and wants structural information
- Provides a SMILES string and wants to identify the compound
- Asks about chemical safety, GHS hazard symbols, or storage conditions
- Asks what products a chemical reaction would produce
- Provides a chemical structure image for recognition

### Should Use
- "苯甲酸的分子结构是什么？"
- "CC(=O)Oc1ccccc1C(=O)O 是什么物质？"
- "苯的安全风险有哪些？"
- "乙酸和乙醇反应生成什么？"

### Should Not Use
- General knowledge questions unrelated to chemistry
- Questions about biology, physics, or other non-chemistry sciences
- Questions that don't involve specific chemical compounds or reactions

## How It Works

This skill calls a local chemistry API service running at `http://localhost:8899`.

**Prerequisites:**
1. Python 3.10+ with dependencies installed (`pip install -r requirements.txt`)
2. Ollama running with qwen3.6-35b-a3b model
3. Chemistry service started: `python -m chemskill.server` (port 8899)

## Tools

### Tool 1: name_to_structure

Convert chemical name to molecular structure. Supports Chinese, English, IUPAC, and common names.

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "name_to_structure", "arguments": {"name": "苯甲酸"}}'
```

Returns: SMILES, molecular formula, molecular weight, IUPAC name, PubChem CID.

### Tool 2: inspect_smiles

Query chemical information from a SMILES string.

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "inspect_smiles", "arguments": {"smiles": "CCO"}}'
```

### Tool 3: safety_info

Query chemical safety information (GHS hazards, danger classifications).

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "safety_info", "arguments": {"query": "苯"}}'
```

### Tool 4: predict_reaction

Predict chemical reaction products, equations, and conditions.

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "predict_reaction", "arguments": {"reactants": "乙酸和乙醇", "conditions": "催化剂硫酸，加热"}}'
```

### Tool 5: ocr_chemistry

Recognize chemical compounds from structure images (requires base64 image).

```bash
curl -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "ocr_chemistry", "arguments": {"image_base64": "<base64>"}}'
```

### Agent Chat (Auto-routing)

Let the LLM automatically decide which tool to call:

```bash
curl -X POST http://localhost:8899/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "苯甲酸的分子结构是什么？"}'
```

## Notes

- All chemistry data comes from PubChem real database, not LLM guesses
- Service runs locally — chemistry data never leaves the machine
- If the service is not running, tool calls will return connection errors
- For Swagger UI testing, visit: http://localhost:8899/docs
