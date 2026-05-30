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
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import ChemAgent
from .config import SkillConfig
from .tools.registry import ToolRegistry
from .tools.name_resolver import NameToStructureTool
from .tools.smiles_inspector import SmilesInspectorTool
from .tools.safety_lookup import SafetyLookupTool
from .tools.reaction_predict import ReactionPredictTool
from .tools.ocr_recognizer import OcrRecognizerTool
from .utils.svg_renderer import smiles_to_svg, is_rdkit_available

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
        "svg_renderer": "rdkit" if is_rdkit_available() else "unavailable",
    }


@app.get("/api/svg/{smiles:path}")
async def render_svg(smiles: str, width: int = 350, height: int = 300):
    """直接通过 SMILES 渲染 SVG 结构图"""
    from fastapi.responses import Response
    svg = smiles_to_svg(smiles, width=width, height=height)
    if svg is None:
        return {"error": "渲染失败，SMILES 无效或 RDKit 未安装"}
    return Response(content=svg, media_type="image/svg+xml")


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
