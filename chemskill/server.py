"""FastAPI 化学工具服务端

纯工具层，不包含内层 Agent（Agent 角色由 QwenPaw 承担）。

端点：
- POST /api/tools/call     调用单个工具
- GET  /api/tools/list      列出所有工具
- GET  /api/health          健康检查
- GET  /api/svg/{smiles}    SMILES -> SVG 结构图
- GET  /api/equation/{eq}   化学方程式渲染
"""

from __future__ import annotations

import re
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

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
from .tools.ocr_recognizer import OcrRecognizerTool

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
    registry.register(OcrRecognizerTool())
    logger.info(f"共注册 {len(registry)} 个工具")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _register_tools()
    logger.info(f"ChemVision Skill 已启动 | 端口: {config.server_port}")
    yield
    logger.info("ChemVision Skill 已关闭")


app = FastAPI(
    title="ChemVision Agent Skill",
    description="AI 化学家工具服务 — PubChem + OPSIN 化学数据查询 + smiles-drawer 结构渲染",
    version="2.1.0",
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


# ── 请求/响应模型 ──

class ToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="工具名称")
    arguments: dict = Field(default_factory=dict, description="工具参数")


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
    success = "error" not in result
    return ToolCallResponse(success=success, result=result)


@app.get("/api/svg/{smiles:path}")
async def get_svg(smiles: str):
    """SMILES -> SVG 分子结构图"""
    smiles_decoded = smiles.strip()
    if not smiles_decoded:
        return HTMLResponse("<p>缺少 smiles 参数</p>", status_code=400)

    safe = _escape_for_js(smiles_decoded)

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<title>ChemVision - structure</title>'
        '<style>body{margin:0;background:#fff;display:flex;align-items:center;justify-content:center;height:100vh}'
        'svg{max-width:100%}</style></head><body>'
        '<svg id="mol" width="500" height="400"></svg>'
        '<script src="/static/smiles-drawer.js"></script>'
        '<script>'
        'var d=new SmilesDrawer.SvgDrawer({width:500,height:400,bondThickness:2,padding:20});'
        f'SmilesDrawer.parse("{safe}",function(t){{d.draw(t,document.getElementById("mol"),"light")}},'
        'function(e){document.body.innerHTML="<p style=color:red;padding:20px>渲染失败: "+e+"</p>"})'
        '</script></body></html>'
    )
    return HTMLResponse(html)


@app.get("/api/equation/{equation:path}")
async def render_equation(equation: str):
    """化学方程式渲染（KaTeX + mhchem）"""
    raw = equation.strip()
    if not raw:
        return HTMLResponse("<p>缺少 equation 参数</p>", status_code=400)

    # mhchem 语法安全过滤：只保留化学方程式合法字符
    safe = _sanitize_equation(raw)
    js_safe = _escape_for_js(safe)

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<title>ChemVision - equation</title>'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.css">'
        '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.js"></script>'
        '<script src="https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/contrib/mhchem.min.js"></script>'
        '<style>body{margin:0;background:#fff;display:flex;align-items:center;justify-content:center;'
        'min-height:100vh;padding:30px;font-family:"Times New Roman",serif}'
        '#eq-box{text-align:center;padding:24px 40px}'
        '.katex{font-size:1.6em}'
        '#title{font-size:13px;color:#888;margin-bottom:16px;font-family:sans-serif}</style></head><body>'
        '<div id="eq-box">'
        '<div id="title">ChemVision 化学方程式</div>'
        '<div id="render"></div></div>'
        '<script>try{katex.render("\\ce{' + js_safe + '}",document.getElementById("render"),'
        '{throwOnError:false,displayMode:true})}catch(e){'
        'document.getElementById("render").innerHTML="<p style=color:red>渲染失败: "+e.message+"</p>"}'
        '</script></body></html>'
    )
    return HTMLResponse(html)


def _escape_for_js(s: str) -> str:
    """转义字符串用于 JS 字符串插值（防 XSS）"""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'").replace('\n', '\\n')


def _sanitize_equation(eq: str) -> str:
    """过滤化学方程式：只保留 mhchem 合法字符"""
    # 允许：字母、数字、+、-、=、<、>、(、)、[、]、{、}、.、空格、\、/、^、_、:、,
    return re.sub(r'[^A-Za-z0-9+\-=<>()\[\]{}.\\/^_ :,]', '', eq)


# ── 启动入口 ──

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
