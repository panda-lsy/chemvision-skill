"""工具4: 化学反应推测

输入反应物和条件，推测产物和反应方程式。
优先通过 Ollama LLM 推测；若 Ollama 不可用，返回 fallback 标记，
由 QwenPaw Agent 自行回答（Agent 本身就是 LLM）。
"""

from __future__ import annotations

from typing import Optional

import httpx

from .registry import ChemTool
from ..config import SkillConfig


class ReactionPredictTool(ChemTool):
    """化学反应推测"""

    def __init__(self, config: Optional[SkillConfig] = None):
        self.config = config or SkillConfig()

    @property
    def name(self) -> str:
        return "predict_reaction"

    @property
    def description(self) -> str:
        return (
            "推测化学反应的产物和条件。"
            "输入反应物名称，返回可能的产物、反应方程式和反应条件。"
            "适用于：用户询问两种物质反应会生成什么、反应条件是什么时调用。"
            "如果返回 fallback=true，说明 Ollama 不可用，请 Agent 自行根据化学知识回答。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "reactants": {
                    "type": "string",
                    "description": "反应物描述，如 '乙酸和乙醇'、'NaOH + HCl'",
                },
                "conditions": {
                    "type": "string",
                    "description": "可选的反应条件，如 '加热'、'催化剂硫酸'",
                },
            },
            "required": ["reactants"],
        }

    async def execute(self, reactants: str = "", conditions: str = "", **kwargs) -> dict:
        r = reactants.strip()
        if not r:
            return {"success": False, "error": "请提供反应物"}

        prompt = self._build_reaction_prompt(r, conditions)

        try:
            url = f"{self.config.ollama_base_url}/api/generate"
            payload = {
                "model": self.config.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2},
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    return self._fallback(r, conditions, f"Ollama 不可用 (HTTP {resp.status_code})")
                data = resp.json()
                answer = data.get("response", "")

            return {
                "success": True,
                "reactants": r,
                "conditions": conditions or "标准条件",
                "prediction": answer,
                "source": "llm_reasoning",
                "disclaimer": "此结果为 LLM 推测，实际反应需以实验验证",
            }

        except (httpx.ConnectError, httpx.ReadTimeout):
            return self._fallback(r, conditions, "Ollama 服务未启动或不可达")
        except Exception as e:
            return self._fallback(r, conditions, str(e))

    @staticmethod
    def _fallback(reactants: str, conditions: str, reason: str) -> dict:
        """Ollama 不可用时，返回 fallback 标记，让 Agent 自行回答"""
        return {
            "success": True,
            "fallback": True,
            "reactants": reactants,
            "conditions": conditions or "标准条件",
            "reason": reason,
            "instruction": (
                "Ollama 本地模型不可用，请 Agent 直接根据化学知识回答。"
                "请给出：1. 反应类型 2. 化学方程式（配平） 3. 反应条件 4. 产物说明。"
                "回答后调用 /api/equation/{方程式} 渲染专业化学方程式图片发给用户。"
            ),
        }

    @staticmethod
    def _build_reaction_prompt(reactants: str, conditions: str) -> str:
        cond_text = f"\n反应条件：{conditions}" if conditions else ""
        return (
            f"你是一位专业的化学家。请根据以下反应物推测化学反应。\n"
            f"反应物：{reactants}{cond_text}\n\n"
            f"请按以下格式回答（中文）：\n"
            f"1. 反应类型（如：酸碱中和、酯化、置换等）\n"
            f"2. 化学方程式（配平后）\n"
            f"3. 反应条件（温度、催化剂、溶剂等）\n"
            f"4. 产物说明\n"
            f"5. 注意事项\n"
        )
