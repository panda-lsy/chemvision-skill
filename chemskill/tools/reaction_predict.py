"""纯数据查询工具：反应物信息查询

输入反应物名称，返回各反应物的化学信息（分子式、分子量、SMILES）。
不进行 LLM 推理 —— 反应推测由 Agent 自行完成。
"""

from __future__ import annotations

import re
from typing import Optional

from .registry import ChemTool
from ..utils.pubchem_client import PubChemClient


class ReactionPredictTool(ChemTool):
    """反应物化学信息查询"""

    def __init__(self, pubchem: Optional[PubChemClient] = None):
        self._pubchem = pubchem or PubChemClient()

    @property
    def name(self) -> str:
        return "predict_reaction"

    @property
    def description(self) -> str:
        return (
            "查询反应物的化学信息（分子式、分子量、SMILES），辅助推测化学反应。"
            "输入反应物名称（中文/英文），返回各物质的化学数据。"
            "Agent 应基于返回数据自行推断反应类型、产物和方程式。"
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
            },
            "required": ["reactants"],
        }

    async def execute(self, reactants: str = "", **kwargs) -> dict:
        r = reactants.strip()
        if not r:
            return {"success": False, "error": "请提供反应物"}

        # 拆分反应物（按 + 、 和 、 与 分割）
        parts = re.split(r'\s*[+＋和与]\s*', r)
        parts = [p.strip() for p in parts if p.strip()]

        results = []
        for part in parts:
            # 尝试中文翻译
            en = _chinese_to_english(part)
            info = await self._pubchem.query_by_name(en or part)
            entry = {"name": part}
            if info.smiles:
                entry.update({
                    "smiles": info.smiles,
                    "molecular_formula": info.molecular_formula or "",
                    "molecular_weight": info.molecular_weight or 0,
                    "iupac_name": info.iupac_name or "",
                    "found": True,
                })
            else:
                entry["found"] = False
                entry["note"] = f"PubChem 未找到 '{part}'，请 Agent 根据化学知识补充"
            results.append(entry)

        return {
            "success": True,
            "reactants": results,
            "agent_instruction": (
                "请根据以上反应物信息，自行推断："
                "1. 反应类型 2. 化学方程式（配平） 3. 反应条件 4. 产物说明。"
                "回答后用 /api/formula/{方程式} 渲染图片发给用户。"
            ),
        }


def _chinese_to_english(chinese: str) -> str | None:
    """常见中文化学名 -> 英文映射"""
    mapping = {
        "水": "water", "酒精": "ethanol", "乙醇": "ethanol",
        "甲醇": "methanol", "丙酮": "acetone", "苯": "benzene",
        "甲苯": "toluene", "苯甲酸": "benzoic acid", "乙酸": "acetic acid",
        "盐酸": "hydrochloric acid", "硫酸": "sulfuric acid",
        "硝酸": "nitric acid", "氢氧化钠": "sodium hydroxide",
        "氢氧化钾": "potassium hydroxide", "氯化钠": "sodium chloride",
        "碳酸钙": "calcium carbonate", "碳酸钠": "sodium carbonate",
        "葡萄糖": "glucose", "蔗糖": "sucrose", "尿素": "urea",
        "阿司匹林": "aspirin", "咖啡因": "caffeine",
        "乙酸乙酯": "ethyl acetate", "苯酚": "phenol",
        "甲醛": "formaldehyde", "乙醛": "acetaldehyde",
        "乙炔": "acetylene", "乙烯": "ethylene", "丙烯": "propylene",
        "环己烷": "cyclohexane", "萘": "naphthalene",
        "吡啶": "pyridine", "呋喃": "furan",
    }
    if chinese in mapping:
        return mapping[chinese]
    clean = chinese.rstrip("溶液固体气体液体")
    return mapping.get(clean)
