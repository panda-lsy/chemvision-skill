"""FastAPI 化学工具服务端

纯数据查询层，不依赖任何 LLM。Agent 角色由 QwenPaw 承担。

端点：
- POST /api/tools/call      调用工具
- GET  /api/tools/list       列出工具
- GET  /api/health           健康检查
- GET  /api/svg/{smiles}     分子结构图
- GET  /api/formula/{eq}     化学方程式渲染
"""

from __future__ import annotations

import re
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import SkillConfig
from .tools.registry import ToolRegistry
from .tools.name_resolver import NameToStructureTool
from .tools.smiles_inspector import SmilesInspectorTool
from .tools.safety_lookup import SafetyLookupTool
from .tools.reaction_predict import ReactionPredictTool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

config = SkillConfig()
registry = ToolRegistry()


def _register_tools() -> None:
    registry.register(NameToStructureTool())
    registry.register(SmilesInspectorTool())
    registry.register(SafetyLookupTool())
    registry.register(ReactionPredictTool())
    logger.info(f"共注册 {len(registry)} 个工具")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _register_tools()
    logger.info(f"ChemVision Skill 已启动 | 端口: {config.server_port}")
    yield
    logger.info("ChemVision Skill 已关闭")


app = FastAPI(
    title="ChemVision Agent Skill",
    description="化学工具服务 — PubChem + OPSIN 数据查询 + 分子结构渲染",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    success: bool
    result: dict


# ── API 路由 ──

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "tools_count": len(registry),
        "tools": [t["name"] for t in registry.list_tools()],
    }


@app.get("/api/tools/list")
async def list_tools():
    return {"tools": registry.list_tools()}


@app.post("/api/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    result = await registry.call(request.tool_name, request.arguments)
    return ToolCallResponse(success="error" not in result, result=result)


@app.get("/api/svg/{smiles:path}")
async def get_svg(smiles: str):
    """SMILES -> 分子结构图（smiles-drawer）"""
    s = smiles.strip()
    if not s:
        return HTMLResponse("<p>缺少 smiles 参数</p>", status_code=400)

    safe = _js_escape(s)
    return HTMLResponse(
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>structure</title>'
        '<style>body{margin:0;background:#fff;display:flex;align-items:center;justify-content:center;height:100vh}'
        'svg{max-width:100%}</style></head><body>'
        '<svg id="m" width="500" height="400"></svg>'
        '<script src="/static/smiles-drawer.js"></script>'
        f'<script>var d=new SmilesDrawer.SvgDrawer({{width:500,height:400,bondThickness:2,padding:20}});'
        f'SmilesDrawer.parse("{safe}",function(t){{d.draw(t,document.getElementById("m"),"light")}},'
        'function(e){document.body.innerHTML="<p style=color:red;padding:20px>"+e+"</p>"})</script></body></html>'
    )


@app.get("/api/formula/{equation:path}")
async def render_formula(equation: str):
    """化学方程式渲染（纯 HTML + CSS，无外部依赖）

    支持：下标数字（H2O）、上标（Fe2+）、箭头（-> <=>）、条件标注
    """
    raw = equation.strip()
    if not raw:
        return HTMLResponse("<p>缺少 equation 参数</p>", status_code=400)

    html_content = _render_chem_html(raw)

    return HTMLResponse(
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>equation</title>'
        '<style>'
        'body{margin:0;background:#fff;display:flex;align-items:center;justify-content:center;'
        'min-height:100vh;padding:30px;font-family:"Times New Roman",Georgia,serif}'
        '.eq{text-align:center;padding:20px 32px;font-size:28px;line-height:1.8;letter-spacing:1px}'
        '.eq sub{font-size:0.7em;vertical-align:sub}'
        '.eq sup{font-size:0.7em;vertical-align:super}'
        '.eq .arrow{margin:0 8px;font-size:1.1em}'
        '.eq .plus{margin:0 6px}'
        '.eq .cond{display:block;font-size:0.55em;color:#666;margin:-4px 0}'
        '#label{font-size:12px;color:#999;text-align:center;margin-bottom:14px;font-family:sans-serif}'
        '</style></head><body><div>'
        '<div id="label">ChemVision</div>'
        f'<div class="eq">{html_content}</div>'
        '</div></body></html>'
    )


def _render_chem_html(eq: str) -> str:
    """将化学方程式纯文本转为带下标/上标的 HTML

    规则：
    - 元素后的数字 → 下标: H2O → H<sub>2</sub>O
    - 数字在最前（配平系数）→ 保持原样: 2H2O
    - ^数字 或 ^{内容} → 上标: Fe^{2+} → Fe<sup>2+</sup>
    - -> → →  <=>  → ⇌
    - 条件文本在方括号内 → 小字: [加热] → <span class="cond">加热</span>
    """
    result = []
    i = 0
    n = len(eq)

    while i < n:
        ch = eq[i]

        # 方括号条件标注
        if ch == '[':
            end = eq.find(']', i)
            if end != -1:
                cond = eq[i + 1:end]
                result.append(f'<span class="cond">{_html_esc(cond)}</span>')
                i = end + 1
                continue

        # 上标: ^{...} 或 ^数字
        if ch == '^':
            i += 1
            if i < n and eq[i] == '{':
                end = eq.find('}', i)
                if end != -1:
                    result.append(f'<sup>{_html_esc(eq[i + 1:end])}</sup>')
                    i = end + 1
                    continue
            elif i < n:
                result.append(f'<sup>{_html_esc(eq[i])}</sup>')
                i += 1
                continue

        # 箭头
        if eq[i:i + 3] == '<=>':
            result.append('<span class="arrow">⇌</span>')
            i += 3
            continue
        if eq[i:i + 2] == '->':
            result.append('<span class="arrow">→</span>')
            i += 2
            continue
        if eq[i:i + 2] == '<-':
            result.append('<span class="arrow">←</span>')
            i += 2
            continue

        # + 号（反应物/产物分隔）
        if ch in ('+', '＋'):
            result.append('<span class="plus">+</span>')
            i += 1
            continue

        # 字母后的数字 → 下标
        if ch.isdigit() and i > 0:
            # 前一个字符是字母或 ) 或 ] → 这是下标
            prev = eq[i - 1]
            if prev.isalpha() or prev in (')', ']', '}'):
                # 收集连续数字
                j = i
                while j < n and eq[j].isdigit():
                    j += 1
                result.append(f'<sub>{eq[i:j]}</sub>')
                i = j
                continue
            # 否则（配平系数）→ 原样输出

        result.append(_html_esc(ch))
        i += 1

    return ''.join(result)


def _html_esc(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _js_escape(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'").replace('\n', '\\n')


def main():
    uvicorn.run(
        "chemskill.server:app",
        host=config.server_host,
        port=config.server_port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
