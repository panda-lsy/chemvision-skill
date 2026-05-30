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
    version="3.1.0",
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
    """化学方程式渲染（纯 HTML + CSS）

    支持：下标（H2O）、上标（Fe^{2+}）、箭头（-> <=>）、条件标注（[加热]在箭头上/下方）
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
        '.eq{display:inline-flex;align-items:center;flex-wrap:nowrap;font-size:28px;letter-spacing:1px}'
        '.eq sub{font-size:0.65em;vertical-align:sub}'
        '.eq sup{font-size:0.65em;vertical-align:super}'
        '.eq .plus{margin:0 6px}'
        '.eq .coef{margin-right:2px}'
        '.arr-box{display:inline-flex;flex-direction:column;align-items:center;'
        'margin:0 10px;position:relative;min-width:48px}'
        '.arr-box .cond{font-size:0.42em;color:#555;line-height:1.2;white-space:nowrap}'
        '.arr-box .sym{font-size:1.1em;line-height:1}'
        '#label{font-size:12px;color:#999;text-align:center;margin-bottom:16px;font-family:sans-serif}'
        '</style></head><body><div>'
        '<div id="label">ChemVision</div>'
        f'<div class="eq">{html_content}</div>'
        '</div></body></html>'
    )


def _render_chem_html(eq: str) -> str:
    """化学方程式纯文本 -> 带下标/上标/箭头条件的 HTML

    规则：
    - 元素后的数字 -> 下标: H2O -> H<sub>2</sub>O
    - 数字在最前（配平系数）-> 保持原样: 2H2O
    - ^{内容} -> 上标: Fe^{2+} -> Fe<sup>2+</sup>
    - -> -> →, <=> -> ⇌
    - [text] 紧邻箭头前 -> 条件在箭头上方
    - [text] 紧邻箭头后 -> 条件在箭头下方
    """
    result = []
    i = 0
    n = len(eq)
    pending_above = []  # 箭头前的条件
    pending_below = []  # 箭头后的条件

    while i < n:
        ch = eq[i]

        # 方括号条件标注
        if ch == '[':
            end = eq.find(']', i)
            if end != -1:
                cond_text = _html_esc(eq[i + 1:end])
                # 先检查后面是否紧跟箭头
                rest = eq[end + 1:].lstrip()
                if rest.startswith('->') or rest.startswith('<=>'):
                    pending_above.append(cond_text)
                else:
                    pending_below.append(cond_text)
                i = end + 1
                continue

        # 上标: ^{...} 或 ^单字符
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

        # 箭头：<=> 或 ->
        arrow_sym = None
        arrow_len = 0
        if eq[i:i + 3] == '<=>':
            arrow_sym, arrow_len = '⇌', 3
        elif eq[i:i + 2] == '->':
            arrow_sym, arrow_len = '→', 2
        elif eq[i:i + 2] == '<-':
            arrow_sym, arrow_len = '←', 2

        if arrow_sym:
            # 检查箭头后是否有紧随的条件（第一个在上，第二个在下）
            j = i + arrow_len
            while j < n and eq[j] == ' ':
                j += 1
            if j < n and eq[j] == '[':
                end2 = eq.find(']', j)
                if end2 != -1:
                    text1 = _html_esc(eq[j + 1:end2])
                    i = end2 + 1
                    # 检查是否还有第二个条件
                    while i < n and eq[i] == ' ':
                        i += 1
                    if i < n and eq[i] == '[':
                        end3 = eq.find(']', i)
                        if end3 != -1:
                            pending_below.append(_html_esc(eq[i + 1:end3]))
                            pending_above.append(text1)
                            i = end3 + 1
                        else:
                            pending_below.append(text1)
                    else:
                        # 只有一个条件 → 放下方
                        pending_below.append(text1)

            # 渲染带条件的箭头
            above_html = '<br>'.join(pending_above) if pending_above else '&nbsp;'
            below_html = '<br>'.join(pending_below) if pending_below else '&nbsp;'
            result.append(
                f'<span class="arr-box">'
                f'<span class="cond">{above_html}</span>'
                f'<span class="sym">{arrow_sym}</span>'
                f'<span class="cond">{below_html}</span>'
                f'</span>'
            )
            pending_above.clear()
            pending_below.clear()
            continue

        # + 号
        if ch in ('+', '＋'):
            result.append('<span class="plus">+</span>')
            i += 1
            continue

        # 字母后的数字 -> 下标
        if ch.isdigit() and i > 0:
            prev = eq[i - 1]
            if prev.isalpha() or prev in (')', ']', '}'):
                j = i
                while j < n and eq[j].isdigit():
                    j += 1
                result.append(f'<sub>{eq[i:j]}</sub>')
                i = j
                continue

        result.append(_html_esc(ch))
        i += 1

    # 如果有未消费的 pending conditions（极端情况），追加
    if pending_above or pending_below:
        result.append(
            '<span class="arr-box"><span class="cond">'
            + '<br>'.join(pending_above + pending_below)
            + '</span><span class="sym">?</span><span class="cond">&nbsp;</span></span>'
        )

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
