"""FastAPI 化学工具服务端

纯工具层，不包含内层 Agent（Agent 角色由 QwenPaw 承担）。

端点：
- POST /api/tools/call   调用单个工具
- GET  /api/tools/list    列出所有工具
- GET  /api/health        健康检查
- GET  /api/svg/{smiles}  SMILES → SVG 结构图渲染
"""

from __future__ import annotations

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

# ── 全局实例 ──
config = SkillConfig()
registry = ToolRegistry()


def _register_tools() -> None:
    """注册所有化学工具"""
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
    version="1.1.0",
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
    """SMILES → SVG 分子结构图（smiles-drawer 前端渲染）

    QwenPaw 用 browser_visible 打开此 URL，截图后发送给用户。
    """
    smiles_decoded = smiles.strip()
    if not smiles_decoded:
        return HTMLResponse("<p>缺少 smiles 参数</p>", status_code=400)

    # 转义 SMILES 中的特殊字符防止 XSS
    safe = smiles_decoded.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>ChemVision - {safe}</title>
<style>
  body {{ margin:0; background:#fff; display:flex; align-items:center; justify-content:center; height:100vh; }}
  svg {{ max-width:100%; }}
</style></head><body>
<svg id="mol" width="500" height="400"></svg>
<script src="/static/smiles-drawer.js"></script>
<script>
  var svgDrawer = new SmilesDrawer.SvgDrawer({{width:500,height:400,bondThickness:2,padding:20}});
  SmilesDrawer.parse("{safe}", function(tree) {{
    svgDrawer.draw(tree, document.getElementById('mol'), 'light');
  }}, function(err) {{
    document.body.innerHTML = '<p style="color:red;padding:20px">SMILES 渲染失败: ' + err + '</p>';
  }});
</script></body></html>"""
    return HTMLResponse(html)


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
