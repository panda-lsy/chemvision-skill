"""FastAPI 服务端入口

提供 HTTP API 接口，支持：
- POST /api/chat         对话接口（Agent 主入口）
- POST /api/tools/call   直接调用工具（跳过 Agent）
- GET  /api/tools/list   列出所有可用工具
- GET  /api/health       健康检查
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import ChemAgent
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

# ── 全局实例 ──
config = SkillConfig()
registry = ToolRegistry()
agent: Optional[ChemAgent] = None


def _register_tools() -> None:
    """注册所有化学工具"""
    pubchem = None  # 各工具内部自行创建 client
    registry.register(NameToStructureTool())
    registry.register(SmilesInspectorTool())
    registry.register(SafetyLookupTool())
    registry.register(ReactionPredictTool())
    registry.register(OcrRecognizerTool())
    logger.info(f"共注册 {len(registry)} 个工具")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent
    _register_tools()
    agent = ChemAgent(config=config, registry=registry)
    logger.info(f"ChemVision Skill 已启动 | 模型: {config.ollama_model} | 端口: {config.server_port}")
    yield
    logger.info("ChemVision Skill 已关闭")


app = FastAPI(
    title="ChemVision Agent Skill",
    description="AI 化学家智能体 - 基于 ≤35B 本地模型驱动化学工具调用",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件（smiles-drawer.js）
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── 请求/响应模型 ──

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入文本")
    history: Optional[list[dict]] = Field(None, description="对话历史")
    image_base64: Optional[str] = Field(None, description="图片 base64（多模态）")


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] = []
    rounds: int = 1
    error: Optional[str] = None


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
        "model": config.ollama_model,
        "tools_count": len(registry),
        "svg_renderer": "smiles-drawer",
    }


@app.get("/render", response_class=HTMLResponse)
async def render_page(smiles: str = "", name: str = "", formula: str = "", weight: str = ""):
    """SMILES 分子结构渲染页面（smiles-drawer SVG）"""
    html_file = STATIC_DIR / "render.html"
    if not html_file.exists():
        return HTMLResponse("<h1>render.html 未找到</h1>", status_code=500)
    return HTMLResponse(html_file.read_text(encoding="utf-8"))


@app.get("/api/svg/{smiles:path}")
async def get_svg(smiles: str):
    """返回自包含 SVG 渲染页面（可截图/嵌入）

    返回一个 HTML 页面，加载后自动渲染 SMILES 结构图。
    QwenPaw 可用 browser_visible 打开后截图展示给用户。
    """
    from urllib.parse import quote as url_quote
    smiles_decoded = smiles.strip()
    if not smiles_decoded:
        return HTMLResponse("<p>缺少 smiles 参数</p>", status_code=400)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ margin:0; background:#fff; display:flex; align-items:center; justify-content:center; height:100vh; }}
  svg {{ max-width:100%; }}
</style></head><body>
<svg id="mol" width="500" height="400"></svg>
<script src="/static/smiles-drawer.js"></script>
<script>
  var svgDrawer = new SmilesDrawer.SvgDrawer({{width:500,height:400,bondThickness:2,padding:20}});
  SmilesDrawer.parse("{smiles_decoded}", function(tree) {{
    svgDrawer.draw(tree, document.getElementById('mol'), 'light');
  }}, function(err) {{
    document.body.innerHTML = '<p style="color:red;padding:20px">渲染失败: ' + err + '</p>';
  }});
</script></body></html>"""
    return HTMLResponse(html)


@app.get("/api/tools/list")
async def list_tools():
    return {"tools": registry.list_tools()}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    result = await agent.chat(
        user_message=request.message,
        history=request.history,
        image_base64=request.image_base64,
    )
    return ChatResponse(
        reply=result.get("reply", ""),
        tool_calls=result.get("tool_calls", []),
        rounds=result.get("rounds", 1),
        error=result.get("error"),
    )


@app.post("/api/tools/call", response_model=ToolCallResponse)
async def call_tool(request: ToolCallRequest):
    result = await registry.call(request.tool_name, request.arguments)
    success = "error" not in result
    return ToolCallResponse(success=success, result=result)


# ── 启动入口 ──

def main():
    """CLI 启动入口"""
    uvicorn.run(
        "chemskill.server:app",
        host=config.server_host,
        port=config.server_port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
