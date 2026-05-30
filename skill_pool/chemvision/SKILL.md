---
name: chemvision
description: Use this skill when the user asks about chemistry — chemical names, molecular structures (SMILES), molecular formulas, molecular weights, safety information (GHS hazards), or chemical reaction predictions. Supports Chinese and English chemical names, IUPAC names, and common names. Calls PubChem and OPSIN real chemistry databases via local API to reduce LLM hallucinations.
metadata:
  skill_version: "1.0.0"
  tags: ["AIPC", "chemistry", "agent", "tool-calling", "pubchem"]
---

# ChemVision AI 化学家

基于本地化学工具 API（PubChem + OPSIN）的化学智能体技能。
所有化学数据来自真实数据库，非 LLM 推测，大幅减少化学幻觉。

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
- Questions that don't involve specific chemical compounds or reactions

## Step 0: Ensure Service Is Running (MUST DO FIRST)

Before calling any chemistry tool, you MUST verify the service is running.
Follow this exact sequence:

### 0.1 Health Check

```bash
curl -s --max-time 3 http://localhost:8899/api/health
```

- If it returns `{"status":"ok",...}` → service is running, go to Step 1.
- If it fails or times out → service is NOT running, go to Step 0.2.

### 0.2 Start the Service

The chemistry service lives at `{this_skill_dir}/chemskill/server.py`.

Find the skill directory path first (it contains `SKILL.md` and `chemskill/` subdirectory), then run:

```bash
cd {this_skill_dir} && pip install -r requirements.txt -q && python -m chemskill.server &
```

Wait 3-5 seconds for the server to start, then re-check health:

```bash
sleep 3 && curl -s --max-time 3 http://localhost:8899/api/health
```

If it still fails, wait a few more seconds and retry once. If it continues to fail, tell the user the service could not start and suggest checking Python/pip.

### 0.3 Service Ready

Once health check passes, proceed with the chemistry tools below.

## Step 1: Call Chemistry Tools

All tools are called via HTTP POST to `http://localhost:8899/api/tools/call`.

### Tool 1: name_to_structure

Convert chemical name to molecular structure. Supports Chinese, English, IUPAC, and common names.

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "name_to_structure", "arguments": {"name": "化学名称"}}'
```

Returns: SMILES, molecular formula, molecular weight, IUPAC name, PubChem CID, source.

### Tool 2: inspect_smiles

Query chemical information from a SMILES string.

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "inspect_smiles", "arguments": {"smiles": "CCO"}}'
```

### Tool 3: safety_info

Query chemical safety information (GHS hazards, danger classifications).

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "safety_info", "arguments": {"query": "苯"}}'
```

### Tool 4: predict_reaction

Predict chemical reaction products, equations, and conditions.

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "predict_reaction", "arguments": {"reactants": "乙酸和乙醇", "conditions": "催化剂硫酸，加热"}}'
```

### Tool 5: ocr_chemistry

Recognize chemical compounds from structure images (requires base64 image).

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "ocr_chemistry", "arguments": {"image_base64": "<base64数据>"}}'
```

### Agent Chat (Auto-routing)

Let the service's built-in Agent automatically decide which tool to call:

```bash
curl -s -X POST http://localhost:8899/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "苯甲酸的分子结构是什么？"}'
```

## Step 2: Present Results

After getting the tool result (JSON), present it to the user in a clear format:

- Show the compound name (Chinese + English if available)
- Show SMILES, molecular formula, molecular weight
- For safety queries, summarize GHS hazards in plain language
- For reaction predictions, format the equation clearly
- If `success` is `false`, explain the error and suggest alternatives

## Notes

- All chemistry data comes from PubChem real database, not LLM guesses
- Service runs locally — chemistry data never leaves the machine
- The service uses Ollama + Qwen3.6-35B-A3B as its internal Agent brain
- For Swagger UI testing: http://localhost:8899/docs
