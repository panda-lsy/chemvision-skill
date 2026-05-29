"""CLI 交互式演示

启动一个交互式命令行界面，直接与 ChemVision Agent 对话。
无需启动 FastAPI 服务，适合快速测试和演示。

使用方式:
    cd chemvision-skill
    python -m demo.demo_cli
"""

from __future__ import annotations

import asyncio
import json
import sys
import os

# 确保 import 路径正确
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemskill.agent import ChemAgent
from chemskill.config import SkillConfig
from chemskill.tools.registry import ToolRegistry
from chemskill.tools.name_resolver import NameToStructureTool
from chemskill.tools.smiles_inspector import SmilesInspectorTool
from chemskill.tools.safety_lookup import SafetyLookupTool
from chemskill.tools.reaction_predict import ReactionPredictTool
from chemskill.tools.ocr_recognizer import OcrRecognizerTool


def setup_agent() -> ChemAgent:
    """初始化 Agent 和所有工具"""
    config = SkillConfig()
    registry = ToolRegistry()
    registry.register(NameToStructureTool())
    registry.register(SmilesInspectorTool())
    registry.register(SafetyLookupTool())
    registry.register(ReactionPredictTool())
    registry.register(OcrRecognizerTool())
    return ChemAgent(config=config, registry=registry)


async def interactive_loop():
    """交互式主循环"""
    print("=" * 60)
    print("  ChemVision Agent Skill — AI 化学家智能体")
    print("  模型: Ollama + Qwen3.6-35B-A3B")
    print("  工具: name_to_structure, inspect_smiles, safety_info,")
    print("        predict_reaction, ocr_chemistry")
    print("=" * 60)
    print()
    print("输入化学问题开始对话，输入 'quit' 或 'q' 退出。")
    print("示例：")
    print("  - 苯甲酸的结构是什么？")
    print("  - 乙醇的分子式和分子量")
    print("  - CC(=O)Oc1ccccc1C(=O)O 是什么物质？")
    print("  - 乙酸和乙醇反应生成什么？")
    print("  - 苯的安全信息")
    print()

    agent = setup_agent()

    while True:
        try:
            user_input = input("🧑 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "q", "exit", "退出"):
            print("再见！")
            break

        print("\n🤖 Agent 思考中...\n")

        result = await agent.chat(user_message=user_input)

        # 打印工具调用过程
        tool_calls = result.get("tool_calls", [])
        if tool_calls:
            print("📋 工具调用记录：")
            for i, tc in enumerate(tool_calls, 1):
                tool_name = tc.get("tool", "?")
                args = tc.get("arguments", {})
                tc_result = tc.get("result", {})
                args_str = json.dumps(args, ensure_ascii=False)
                success = "error" not in tc_result or not tc_result.get("error")
                status = "✅" if success else "❌"
                print(f"  {i}. {status} {tool_name}({args_str})")
            print()

        # 打印回答
        reply = result.get("reply", "")
        print(f"🔬 Agent:\n{reply}\n")
        print(f"  [共 {result.get('rounds', 1)} 轮工具调用]")
        print("-" * 60)


def main():
    asyncio.run(interactive_loop())


if __name__ == "__main__":
    main()
