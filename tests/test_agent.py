"""Agent 集成测试

测试 Agent 的 function calling 路由逻辑。
使用 mock Ollama 响应，无需实际模型运行。
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemskill.agent import ChemAgent
from chemskill.config import SkillConfig
from chemskill.tools.registry import ToolRegistry
from chemskill.tools.name_resolver import NameToStructureTool


class TestAgentBasic:
    """Agent 基础功能测试"""

    def _create_agent(self) -> ChemAgent:
        config = SkillConfig()
        config.ollama_base_url = "http://mock:11434"
        config.ollama_model = "test-model"
        registry = ToolRegistry()
        registry.register(NameToStructureTool())
        return ChemAgent(config=config, registry=registry)

    def test_agent_creation(self):
        agent = self._create_agent()
        assert agent is not None
        assert agent.config.ollama_model == "test-model"

    def test_system_prompt_loading(self):
        agent = self._create_agent()
        prompt = agent._get_system_prompt()
        assert "化学" in prompt
        assert "SMILES" in prompt or "smiles" in prompt.lower()

    def test_tool_registry_connected(self):
        agent = self._create_agent()
        tools = agent.registry.to_openai_tools()
        assert len(tools) >= 1
        assert tools[0]["function"]["name"] == "name_to_structure"


class TestAgentChat:
    """Agent 对话测试（mock Ollama 响应）"""

    @pytest.mark.asyncio
    async def test_direct_reply_no_tools(self):
        """测试 LLM 直接回复（无需工具调用）"""
        agent = self._create_agent()

        # Mock Ollama 返回直接文本回复
        mock_response = {
            "message": {
                "role": "assistant",
                "content": "水的化学式是 H2O，由两个氢原子和一个氧原子组成。",
            }
        }
        with patch.object(agent, "_call_ollama", return_value=mock_response["message"]):
            result = await agent.chat("水的化学式是什么？")
            assert "reply" in result
            assert "H2O" in result["reply"] or "h2o" in result["reply"].lower()
            assert result["rounds"] == 1
            assert result["tool_calls"] == []

    @pytest.mark.asyncio
    async def test_ollama_unavailable(self):
        """测试 Ollama 不可用时的错误处理"""
        agent = self._create_agent()

        with patch.object(agent, "_call_ollama", return_value=None):
            result = await agent.chat("测试")
            assert result.get("error") == "ollama_unavailable"
            assert "不可用" in result["reply"]

    def _create_agent(self) -> ChemAgent:
        config = SkillConfig()
        config.ollama_base_url = "http://mock:11434"
        config.ollama_model = "test-model"
        registry = ToolRegistry()
        registry.register(NameToStructureTool())
        return ChemAgent(config=config, registry=registry)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
