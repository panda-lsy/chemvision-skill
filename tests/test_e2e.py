"""端到端验证测试

需要实际运行 Ollama + 模型才能通过。
跳过标记: @pytest.mark.skipif(not ollama_available(), reason="Ollama not running")

运行方式:
    cd chemvision-skill
    pytest tests/test_e2e.py -v --run-e2e
"""

import pytest
import asyncio
import httpx

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemskill.agent import ChemAgent
from chemskill.config import SkillConfig
from chemskill.tools.registry import ToolRegistry
from chemskill.tools.name_resolver import NameToStructureTool
from chemskill.tools.smiles_inspector import SmilesInspectorTool
from chemskill.tools.safety_lookup import SafetyLookupTool


def ollama_available() -> bool:
    """检查 Ollama 是否在运行"""
    try:
        resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False


needs_ollama = pytest.mark.skipif(
    not ollama_available(), reason="Ollama not running"
)


def create_test_agent() -> ChemAgent:
    config = SkillConfig()
    registry = ToolRegistry()
    registry.register(NameToStructureTool())
    registry.register(SmilesInspectorTool())
    registry.register(SafetyLookupTool())
    return ChemAgent(config=config, registry=registry)


class TestToolDirect:
    """直接工具调用端到端测试（仅需网络，不需 Ollama）"""

    @pytest.mark.asyncio
    async def test_name_to_structure_ethanol(self):
        """PubChem 解析乙醇"""
        tool = NameToStructureTool()
        result = await tool.execute(name="ethanol")
        assert result["success"] is True
        assert "CCO" in result["smiles"]
        assert result["molecular_formula"] == "C2H6O"

    @pytest.mark.asyncio
    async def test_name_to_structure_aspirin(self):
        """PubChem 解析阿司匹林"""
        tool = NameToStructureTool()
        result = await tool.execute(name="aspirin")
        assert result["success"] is True
        assert result["molecular_formula"] == "C9H8O4"

    @pytest.mark.asyncio
    async def test_name_to_structure_chinese(self):
        """中文名解析 - 乙醇"""
        tool = NameToStructureTool()
        result = await tool.execute(name="乙醇")
        assert result["success"] is True
        assert "CCO" in result["smiles"]

    @pytest.mark.asyncio
    async def test_smiles_inspector(self):
        """SMILES 信息查询"""
        tool = SmilesInspectorTool()
        result = await tool.execute(smiles="CCO")
        assert result["success"] is True
        assert "Ethanol" in result.get("iupac_name", "") or "ethanol" in result.get("iupac_name", "").lower()

    @pytest.mark.asyncio
    async def test_name_not_found(self):
        """查询不存在的化合物"""
        tool = NameToStructureTool()
        result = await tool.execute(name="超级无敌化合物XYZ12345不存在")
        assert result["success"] is False


class TestAgentE2E:
    """Agent 完整对话端到端测试（需要 Ollama 运行）"""

    @needs_ollama
    @pytest.mark.asyncio
    async def test_agent_chat_chemistry(self):
        """Agent 化学问答"""
        agent = create_test_agent()
        result = await agent.chat("乙醇的 SMILES 是什么？分子式是什么？")
        assert "reply" in result
        assert len(result["reply"]) > 10
        # 应该有工具调用
        assert len(result["tool_calls"]) > 0

    @needs_ollama
    @pytest.mark.asyncio
    async def test_agent_chat_general(self):
        """Agent 一般化学问题"""
        agent = create_test_agent()
        result = await agent.chat("什么是有机化学？")
        assert "reply" in result
        assert len(result["reply"]) > 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
