"""化学工具单元测试

测试各个化学工具的核心逻辑，无需 Ollama 或网络连接。
使用 mock 隔离外部 API 调用。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemskill.utils.smiles_utils import (
    validate_smiles,
    normalize_smiles,
    is_likely_smiles,
)


# ── SMILES 工具测试 ──

class TestSmilesUtils:
    """SMILES 验证和规范化工具测试"""

    def test_validate_valid_smiles(self):
        assert validate_smiles("CCO") is True  # 乙醇
        assert validate_smiles("c1ccccc1") is True  # 苯
        assert validate_smiles("CC(=O)Oc1ccccc1C(=O)O") is True  # 阿司匹林
        assert validate_smiles("[Na+].[Cl-]") is True  # 氯化钠

    def test_validate_invalid_smiles(self):
        assert validate_smiles("") is False
        assert validate_smiles("  ") is False
        assert validate_smiles("hello world") is False
        assert validate_smiles("CC(") is False  # 括号不匹配
        assert validate_smiles("CC)") is False  # 括号不匹配
        assert validate_smiles("CC[") is False  # 方括号不匹配

    def test_normalize_smiles(self):
        assert normalize_smiles("  CCO  ") == "CCO"
        assert normalize_smiles('"CCO"') == "CCO"
        assert normalize_smiles("SMILES: CCO") == "CCO"
        assert normalize_smiles("smiles：CCO") == "CCO"
        assert normalize_smiles("") == ""

    def test_is_likely_smiles(self):
        assert is_likely_smiles("CCO") is True
        assert is_likely_smiles("c1ccccc1") is True
        assert is_likely_smiles("苯甲酸") is False
        assert is_likely_smiles("hello") is False
        assert is_likely_smiles("") is False


# ── 工具注册表测试 ──

class TestToolRegistry:
    """工具注册表测试"""

    def test_register_and_list(self):
        from chemskill.tools.registry import ToolRegistry

        registry = ToolRegistry()
        assert len(registry) == 0

        # 创建一个 mock 工具
        tool = MagicMock()
        tool.name = "test_tool"
        tool.description = "A test tool"
        tool.parameters = {"type": "object", "properties": {}}
        tool.to_openai_schema.return_value = {
            "type": "function",
            "function": {"name": "test_tool", "description": "A test tool"},
        }

        registry.register(tool)
        assert len(registry) == 1
        assert "test_tool" in registry

        tools_list = registry.list_tools()
        assert len(tools_list) == 1
        assert tools_list[0]["name"] == "test_tool"

    def test_call_unknown_tool(self):
        from chemskill.tools.registry import ToolRegistry

        registry = ToolRegistry()

        result = asyncio.get_event_loop().run_until_complete(
            registry.call("nonexistent", {})
        )
        assert "error" in result


# ── PubChem 客户端 Mock 测试 ──

class TestNameResolver:
    """名称解析工具测试（mock PubChem）"""

    def test_chinese_mapping(self):
        from chemskill.tools.name_resolver import NameToStructureTool

        tool = NameToStructureTool()
        assert tool._chinese_to_english("乙醇") == "ethanol"
        assert tool._chinese_to_english("苯甲酸") == "benzoic acid"
        assert tool._chinese_to_english("水") == "water"
        assert tool._chinese_to_english("未知化合物XYZ") is None


# ── 工具 Schema 测试 ──

class TestToolSchemas:
    """验证所有工具的 schema 格式正确"""

    def _get_all_tools(self):
        from chemskill.tools.name_resolver import NameToStructureTool
        from chemskill.tools.smiles_inspector import SmilesInspectorTool
        from chemskill.tools.safety_lookup import SafetyLookupTool
        from chemskill.tools.reaction_predict import ReactionPredictTool
        from chemskill.tools.ocr_recognizer import OcrRecognizerTool

        return [
            NameToStructureTool(),
            SmilesInspectorTool(),
            SafetyLookupTool(),
            ReactionPredictTool(),
            OcrRecognizerTool(),
        ]

    def test_all_tools_have_name(self):
        for tool in self._get_all_tools():
            assert isinstance(tool.name, str) and len(tool.name) > 0

    def test_all_tools_have_description(self):
        for tool in self._get_all_tools():
            assert isinstance(tool.description, str) and len(tool.description) > 10

    def test_all_tools_have_parameters(self):
        for tool in self._get_all_tools():
            params = tool.parameters
            assert params.get("type") == "object"
            assert "properties" in params

    def test_openai_schema_format(self):
        for tool in self._get_all_tools():
            schema = tool.to_openai_schema()
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
