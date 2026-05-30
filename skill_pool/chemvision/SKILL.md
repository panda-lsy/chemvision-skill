---
name: chemvision
description: Use this skill when the user asks about chemistry — chemical names, molecular structures (SMILES), molecular formulas, molecular weights, safety information (GHS hazards), or chemical reaction predictions. Supports Chinese and English chemical names, IUPAC names, and common names. Calls PubChem and OPSIN real chemistry databases via local API to reduce LLM hallucinations. Returns molecular structure images.
metadata:
  skill_version: "2.0.0"
  tags: ["AIPC", "chemistry", "agent", "tool-calling", "pubchem"]
---

# ChemVision AI 化学家

化学工具服务 — 通过 PubChem 和 OPSIN 真实数据库查询化学信息，支持分子结构图渲染。

## When to Use

Use this skill when the user:
- Asks about a chemical compound's structure, SMILES, molecular formula, or molecular weight
- Provides a chemical name (Chinese or English) and wants structural information
- Provides a SMILES string and wants to identify the compound
- Asks about chemical safety, GHS hazard symbols, or storage conditions
- Asks what products a chemical reaction would produce
- Provides a chemical structure image for recognition

## Step 0: Ensure Service Is Running (MUST DO FIRST)

```bash
cd {this_skill_dir} && python manage.py status
```

- If `"status": "running"` → proceed to Step 1.
- If `"status": "not_running"` → start it:

```bash
cd {this_skill_dir} && python manage.py start
```

To stop the service safely (does NOT kill QwenPaw):

```bash
cd {this_skill_dir} && python manage.py stop
```

## Step 1: Call a Tool

All tools are called via POST to `http://localhost:8899/api/tools/call`.

### name_to_structure — 化学名称 → 结构

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "name_to_structure", "arguments": {"name": "苯甲酸"}}'
```

### inspect_smiles — SMILES → 化学信息

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "inspect_smiles", "arguments": {"smiles": "CCO"}}'
```

### safety_info — 化学品安全信息

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "safety_info", "arguments": {"query": "苯"}}'
```

### predict_reaction — 化学反应推测

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "predict_reaction", "arguments": {"reactants": "乙酸和乙醇", "conditions": "催化剂硫酸，加热"}}'
```

### ocr_chemistry — 化学结构图片识别

```bash
curl -s -X POST http://localhost:8899/api/tools/call \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "ocr_chemistry", "arguments": {"image_base64": "<base64>"}}'
```

## Step 2: Show the Result

### Text data

Present compound name, SMILES, molecular formula, molecular weight clearly.

### Structure image

When the result contains `svg_url`, render and send the molecular structure image to the user:

1. **Open the SVG URL** in a browser:

```json
{"action": "open", "url": "http://localhost:8899/api/svg/CCO"}
```

2. **Take a screenshot** of the rendered page and save it to a temporary file (e.g. `chem_structure.png`).

3. **Send the image file** to the user using `send_file_to_user`:

```json
send_file_to_user(file_path="chem_structure.png", caption="分子结构图")
```

### Chemical equation rendering

After answering a reaction question, render the equation as a professional image:

1. **Format the equation** using mhchem `\ce{}` notation:
   - Use `->` for reactions, `<=>` for equilibrium
   - Subscripts: `H2O`, `CH3COOH`
   - Superscripts: `Fe^{2+}`, `SO4^{2-}`
   - States: `(g)`, `(l)`, `(s)`, `(aq)`
   - Conditions above arrow: `->[\\text{催化剂}][\\text{加热}]`

2. **Open the equation URL** in a browser:

```
http://localhost:8899/api/equation/{equation}
```

For example:
```
http://localhost:8899/api/equation/CH3COOH+C2H5OH<=>[\text{浓硫酸}][\text{加热}]CH3COOC2H5+H2O
```

3. **Screenshot and send** using `send_file_to_user`.

### Fallback: Ollama not available

If `predict_reaction` returns `fallback=true`, the Agent should:
1. Answer the reaction question directly using its own chemistry knowledge
2. Render the equation via `/api/equation/{equation}` and send the image

## Notes

- All chemistry data comes from PubChem real database, not LLM guesses
- Service runs locally — chemistry data never leaves the machine
- Use `python manage.py start/stop/status` to control the service
- For Swagger UI: http://localhost:8899/docs
