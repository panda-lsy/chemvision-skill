"""工具5: 化学结构图片 OCR 识别

输入化学结构图片（base64），通过多模态 LLM 识别化合物。
数据源：Ollama 多模态 LLM（Qwen2.5-VL 或类似）
"""

from __future__ import annotations

import base64
from typing import Optional

import httpx

from .registry import ChemTool
from ..config import SkillConfig


class OcrRecognizerTool(ChemTool):
    """化学结构图片识别"""

    def __init__(self, config: Optional[SkillConfig] = None):
        self.config = config or SkillConfig()

    @property
    def name(self) -> str:
        return "ocr_chemistry"

    @property
    def description(self) -> str:
        return (
            "从化学结构图片中识别化合物。"
            "输入图片的 base64 编码，返回识别到的化学名称和结构信息。"
            "适用于：用户提供化学结构图片需要识别时调用。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "image_base64": {
                    "type": "string",
                    "description": "图片的 base64 编码字符串（支持 PNG/JPG）",
                },
                "question": {
                    "type": "string",
                    "description": "可选的额外问题，如 '这是什么物质？分子式是什么？'",
                },
            },
            "required": ["image_base64"],
        }

    async def execute(
        self, image_base64: str = "", question: str = "", **kwargs
    ) -> dict:
        if not image_base64:
            return {"success": False, "error": "请提供图片 base64 数据"}

        # 清理 base64 前缀
        b64 = image_base64
        if "," in b64:
            b64 = b64.split(",", 1)[1]

        q = question or "请识别图片中的化学结构式，告诉我：1. 这是什么化合物？2. 化学名称 3. 推测的 SMILES 4. 分子式"

        try:
            url = f"{self.config.ollama_base_url}/api/chat"
            payload = {
                "model": self.config.ollama_model,
                "messages": [
                    {
                        "role": "user",
                        "content": q,
                        "images": [b64],
                    }
                ],
                "stream": False,
                "options": {"temperature": 0.1},
            }
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    return {
                        "success": False,
                        "error": f"多模态推理失败 (HTTP {resp.status_code})",
                    }
                data = resp.json()
                answer = data.get("message", {}).get("content", "")

            return {
                "success": True,
                "recognition": answer,
                "source": "multimodal_llm",
                "disclaimer": "图片识别结果为 LLM 推测，关键数据请通过 PubChem 验证",
            }

        except httpx.ConnectError:
            return {
                "success": False,
                "error": "无法连接 Ollama 服务，请确认 Ollama 已启动",
            }
        except Exception as e:
            return {"success": False, "error": f"识别失败: {e}"}
