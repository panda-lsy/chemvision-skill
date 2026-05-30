---
name: chemvision
description: Use this skill when the user asks about chemistry — chemical names, molecular structures (SMILES), molecular formulas, molecular weights, safety information (GHS hazards), or chemical reaction predictions. Supports Chinese and English chemical names, IUPAC names, and common names. Calls PubChem and OPSIN real chemistry databases via local API to reduce LLM hallucinations. Can render molecular structure SVG images.
metadata:
  skill_version: "1.1.0"
  tags: ["AIPC", "chemistry", "agent", "tool-calling", "pubchem"]
---

# ChemVision AI 化学家

基于本地化学工具 API（PubChem + OPSIN）的化学智能体技能。
所有化学数据来自真实数据库，非 LLM 推测，大幅减少化学幻觉。
支持分子结构图渲染（smiles-drawer SVG）。

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

### 0.1 Check Status

```bash
cd {this_skill_dir} && python manage.py status
```

- If output shows `"status": "running"` → service is ready, go to Step 1.
- If output shows `"status": "not_running"` → go to Step 0.2.

### 0.2 Start Service

```bash
cd {this_skill_dir} && python manage.py start
```

This starts the service as a **detached background process** — it will NOT be killed when your session ends, and will NOT interfere with QwenPaw.

Wait for the output to show `"status": "started"`, then proceed.

### 0.3 Stop Service (when done)

```bash
cd {this_skill_dir} && python manage.py stop
```

This safely stops only the chemistry service, without affecting QwenPaw or other Python processes.

### 0.4 Restart (if needed)

```bash
cd {this_skill_dir} && python manage.py restart
```

## Step 1: Call Chemistry Tools

All tools are called via HTTP POST to `http://localhost:8899/api/tools/call`.

### Tool 1: name_to_structure

Convert chemical name to molecular structure. Returns SMILES, molecular formula, molecular weight, **render_url** (full info page), and **svg_url** (structure image page).

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "name_to_structure", "arguments": {"name": "苯甲酸"}}'
```

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
  -d '{"tool_name": "ocr_chemistry", "arguments": {"image_base64": "<base64>"}}'
```

## Step 2: Display Results

### Show text results

Present compound name (Chinese + English), SMILES, molecular formula, molecular weight in a clear format.

### Show structure image

When the tool result contains `svg_url`, open it in a browser to show the molecular structure:

```json
{"action": "open", "url": "http://localhost:8899/api/svg/c1ccc(cc1)C(=O)O"}
```

This shows a clean molecular structure diagram that can be screenshotted.

When the result contains `render_url`, it shows a full info card with structure + chemical data:

```json
{"action": "open", "url": "http://localhost:8899/render?smiles=c1ccc(cc1)C(=O)O&name=benzoic+acid&formula=C7H6O2&weight=122.12"}
```

### Screenshot and send

After opening the URL, take a snapshot/screenshot and send the image to the user along with the text chemical data.

## Notes

- All chemistry data comes from PubChem real database, not LLM guesses
- Service runs locally — chemistry data never leaves the machine
- Use `python manage.py start/stop/status` to control the service (DO NOT use `python -m chemskill.server &`)
- For Swagger UI testing: http://localhost:8899/docs
