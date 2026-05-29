"""Agent 核心：Ollama 对接 + Function Calling 路由

核心流程：
1. 接收用户消息
2. 调用 Ollama（Qwen3.6-35B-A3B）获取决策
3. 如果 LLM 返回 tool_calls，分发到对应工具执行
4. 将工具结果回传 LLM，获取最终回答
5. 支持多轮工具调用（Agent Loop）
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from .config import SkillConfig
from .tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ChemAgent:
    """化学智能体"""

    def __init__(
        self,
        config: Optional[SkillConfig] = None,
        registry: Optional[ToolRegistry] = None,
    ):
        self.config = config or SkillConfig()
        self.registry = registry or ToolRegistry()
        self._system_prompt: str | None = None

    def _get_system_prompt(self) -> str:
        """获取完整系统提示词（缓存）"""
        if self._system_prompt is None:
            base = self.config.load_system_prompt()
            guidance = self.config.load_tool_guidance()
            self._system_prompt = base
            if guidance:
                self._system_prompt += "\n\n" + guidance
        return self._system_prompt

    async def chat(
        self,
        user_message: str,
        history: Optional[list[dict]] = None,
        image_base64: Optional[str] = None,
    ) -> dict:
        """主对话入口

        Args:
            user_message: 用户输入文本
            history: 可选的对话历史
            image_base64: 可选的图片 base64（多模态）

        Returns:
            {"reply": str, "tool_calls": list, "rounds": int}
        """
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._get_system_prompt()},
        ]
        if history:
            messages.extend(history)

        # 构造用户消息
        user_msg: dict[str, Any] = {"role": "user", "content": user_message}
        if image_base64:
            user_msg["images"] = [image_base64]
        messages.append(user_msg)

        # 获取可用工具列表
        tools = self.registry.to_openai_tools()

        # Agent Loop：支持多轮工具调用
        all_tool_calls: list[dict] = []
        for round_idx in range(self.config.max_tool_rounds):
            logger.info(f"Agent 轮次 {round_idx + 1}/{self.config.max_tool_rounds}")

            # 调用 Ollama
            llm_response = await self._call_ollama(messages, tools)

            if llm_response is None:
                return {
                    "reply": "抱歉，模型服务暂时不可用，请确认 Ollama 已启动。",
                    "tool_calls": all_tool_calls,
                    "rounds": round_idx + 1,
                    "error": "ollama_unavailable",
                }

            # 检查是否有 tool_calls
            tool_calls = llm_response.get("tool_calls", [])
            if not tool_calls:
                # 没有工具调用，直接返回文本回答
                content = llm_response.get("content", "")
                return {
                    "reply": content,
                    "tool_calls": all_tool_calls,
                    "rounds": round_idx + 1,
                }

            # 有工具调用，执行并收集结果
            assistant_msg = {
                "role": "assistant",
                "content": llm_response.get("content", ""),
                "tool_calls": tool_calls,
            }
            messages.append(assistant_msg)

            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                try:
                    arguments = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}

                logger.info(f"调用工具: {tool_name}({arguments})")
                result = await self.registry.call(tool_name, arguments)

                all_tool_calls.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "result": result,
                })

                # 将工具结果回传给 LLM
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        # 超过最大轮次，做最后一次调用获取文本回答
        final_response = await self._call_ollama(messages, [])
        content = final_response.get("content", "") if final_response else "达到最大工具调用轮数，已停止。"
        return {
            "reply": content,
            "tool_calls": all_tool_calls,
            "rounds": self.config.max_tool_rounds,
        }

    async def _call_ollama(
        self, messages: list[dict], tools: list[dict]
    ) -> Optional[dict]:
        """调用 Ollama Chat API"""
        url = f"{self.config.ollama_base_url}/api/chat"

        payload: dict[str, Any] = {
            "model": self.config.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.agent_temperature,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                logger.info(f"Ollama 请求: model={self.config.ollama_model}, messages={len(messages)}")
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.error(f"Ollama 错误: HTTP {resp.status_code} - {resp.text}")
                    return None
                data = resp.json()
                return data.get("message", {})
        except httpx.ConnectError:
            logger.error(f"无法连接 Ollama: {url}")
            return None
        except Exception as e:
            logger.error(f"Ollama 调用异常: {e}", exc_info=True)
            return None

    async def chat_simple(self, user_message: str) -> str:
        """简化版对话，只返回文本回复"""
        result = await self.chat(user_message)
        return result.get("reply", "")
