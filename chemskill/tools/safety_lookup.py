"""工具3: 化学品安全信息查询

输入化学名称或 SMILES，查询 GHS 危险标识、安全数据等。
数据源：PubChem Safety and Hazards 数据
"""

from __future__ import annotations

from typing import Optional

from .registry import ChemTool
from ..utils.pubchem_client import PubChemClient


class SafetyLookupTool(ChemTool):
    """化学品安全信息查询"""

    def __init__(self, pubchem: Optional[PubChemClient] = None):
        self._pubchem = pubchem or PubChemClient()

    @property
    def name(self) -> str:
        return "safety_info"

    @property
    def description(self) -> str:
        return (
            "查询化学品的安全信息，包括 GHS 危险标识、危害分类、安全提示等。"
            "输入化学名称或 SMILES，返回安全数据摘要。"
            "适用于：用户询问化学品危险性、安全注意事项时调用。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "化学名称或 SMILES，如 '苯'、'ethanol'、'CCO'",
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str = "", **kwargs) -> dict:
        q = query.strip()
        if not q:
            return {"success": False, "error": "请输入化学名称或 SMILES"}

        result = await self._pubchem.get_safety_info(q)

        if result.get("error") == "not_found":
            return {
                "success": False,
                "query": q,
                "error": f"未找到 '{q}' 对应的化合物安全信息",
            }

        if result.get("error"):
            return {
                "success": False,
                "query": q,
                "error": result["error"],
            }

        return {
            "success": True,
            "query": q,
            "cid": result.get("cid"),
            "name": result.get("name"),
            "formula": result.get("formula"),
            "weight": result.get("weight"),
            "safety": result.get("safety", {}),
            "source": "pubchem",
            "message": "安全数据来自 PubChem，仅供参考，具体安全操作请查阅权威 SDS",
        }
