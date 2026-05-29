"""API 调用演示

演示如何通过 HTTP API 调用 ChemVision Skill。
需要先启动 FastAPI 服务: python -m chemskill.server

使用方式:
    python -m demo.demo_api
"""

from __future__ import annotations

import asyncio
import json
import sys
import os

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8899"


async def check_health():
    """检查服务状态"""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{BASE_URL}/api/health")
        data = resp.json()
        print(f"服务状态: {data['status']}")
        print(f"模型: {data['model']}")
        print(f"工具数: {data['tools_count']}")
        return data


async def list_tools():
    """列出所有工具"""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{BASE_URL}/api/tools/list")
        data = resp.json()
        print("\n可用工具：")
        for tool in data["tools"]:
            print(f"  - {tool['name']}: {tool['description'][:50]}...")
        return data


async def call_tool_direct(tool_name: str, arguments: dict):
    """直接调用工具（不经过 Agent）"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{BASE_URL}/api/tools/call",
            json={"tool_name": tool_name, "arguments": arguments},
        )
        data = resp.json()
        print(f"\n工具 [{tool_name}] 结果:")
        print(json.dumps(data["result"], indent=2, ensure_ascii=False))
        return data


async def chat_with_agent(message: str):
    """与 Agent 对话"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{BASE_URL}/api/chat",
            json={"message": message},
        )
        data = resp.json()
        print(f"\n🧑 用户: {message}")
        print(f"\n📋 工具调用 ({len(data.get('tool_calls', []))} 次):")
        for tc in data.get("tool_calls", []):
            print(f"  - {tc['tool']}({json.dumps(tc['arguments'], ensure_ascii=False)})")
        print(f"\n🔬 Agent ({data.get('rounds', 1)} 轮):\n{data['reply']}")
        return data


async def main():
    print("=" * 60)
    print("  ChemVision Skill API 演示")
    print("=" * 60)

    # 1. 健康检查
    print("\n[1] 服务健康检查")
    try:
        await check_health()
    except httpx.ConnectError:
        print("❌ 无法连接服务，请先启动: python -m chemskill.server")
        return

    # 2. 列出工具
    print("\n[2] 列出工具")
    await list_tools()

    # 3. 直接工具调用
    print("\n[3] 直接工具调用 - name_to_structure('ethanol')")
    await call_tool_direct("name_to_structure", {"name": "ethanol"})

    # 4. Agent 对话
    print("\n[4] Agent 对话 - 化学名称解析")
    await chat_with_agent("乙醇的分子结构是什么？请告诉我 SMILES 和分子式")

    print("\n[5] Agent 对话 - 安全查询")
    await chat_with_agent("苯有哪些安全风险？")


if __name__ == "__main__":
    asyncio.run(main())
