"""工具1: 化学名称→SMILES 结构解析

输入化学名称（中文/英文/IUPAC/俗名），输出 SMILES、分子式、分子量等结构信息。
数据源：PubChem API + OPSIN（双源容错）
"""

from __future__ import annotations

import re
from typing import Optional

from .registry import ChemTool
from ..utils.pubchem_client import PubChemClient
from ..utils.opsin_client import OpsinClient
from ..utils.smiles_utils import normalize_smiles, is_likely_smiles
from ..utils.svg_renderer import build_render_url, build_svg_url


class NameToStructureTool(ChemTool):
    """化学名称解析为分子结构"""

    def __init__(
        self,
        pubchem: Optional[PubChemClient] = None,
        opsin: Optional[OpsinClient] = None,
    ):
        self._pubchem = pubchem or PubChemClient()
        self._opsin = opsin or OpsinClient()

    @property
    def name(self) -> str:
        return "name_to_structure"

    @property
    def description(self) -> str:
        return (
            "将化学名称转换为分子结构信息。"
            "支持中文名、英文名、IUPAC名、俗名等输入。"
            "返回 SMILES、分子式、分子量、标准名称等。"
            "适用于：用户询问某化学物质的结构时调用。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "化学名称，如'苯甲酸'、'aspirin'、'ethanol'、'2-甲基丙烷'",
                },
            },
            "required": ["name"],
        }

    async def execute(self, name: str = "", **kwargs) -> dict:
        """执行名称→结构解析"""
        query = name.strip()
        if not query:
            return {"success": False, "error": "请输入化学名称"}

        # 如果输入已经是 SMILES 格式，直接跳转到 SMILES 查询
        if is_likely_smiles(query):
            info = await self._pubchem.query_by_smiles(normalize_smiles(query))
            if info.smiles:
                return self._build_success(info, query, source="pubchem_direct")

        # 中文名检测
        is_chinese = bool(re.search(r'[一-鿿]', query))

        # 1. 直接用名称查 PubChem
        info = await self._pubchem.query_by_name(query)
        if info.smiles:
            return self._build_success(info, query, source="pubchem")

        # 2. 如果是中文，尝试常见翻译映射
        if is_chinese:
            translated = self._chinese_to_english(query)
            if translated:
                info = await self._pubchem.query_by_name(translated)
                if info.smiles:
                    return self._build_success(
                        info, query, source="pubchem+translation", english_hint=translated
                    )

        # 3. OPSIN 解析（仅英文）
        if not is_chinese:
            opsin_result = await self._opsin.query(query)
            if opsin_result.smiles:
                # 用 SMILES 回查 PubChem 获取完整信息
                pubchem_info = await self._pubchem.query_by_smiles(opsin_result.smiles)
                if pubchem_info.smiles:
                    return self._build_success(
                        pubchem_info, query, source="opsin+pubchem"
                    )
                return {
                    "success": True,
                    "query": query,
                    "smiles": opsin_result.smiles,
                    "molecular_formula": opsin_result.molecular_formula or "",
                    "molecular_weight": opsin_result.molecular_weight or 0,
                    "iupac_name": opsin_result.iupac_name or query,
                    "source": "opsin",
                    "message": "由 OPSIN 解析成功，未能从 PubChem 获取补充信息",
                    "render_url": build_render_url(opsin_result.smiles, name=opsin_result.iupac_name),
                    "svg_url": build_svg_url(opsin_result.smiles),
                }

        # 4. 全部失败
        return {
            "success": False,
            "query": query,
            "error": f"未能解析化学名称 '{query}'，请检查名称是否正确，或尝试使用英文 IUPAC 名称",
        }

    def _build_success(
        self,
        info,
        original_query: str,
        source: str = "pubchem",
        english_hint: Optional[str] = None,
    ) -> dict:
        result = {
            "success": True,
            "query": original_query,
            "smiles": info.smiles,
            "molecular_formula": info.molecular_formula or "",
            "molecular_weight": info.molecular_weight or 0,
            "iupac_name": info.iupac_name or "",
            "cid": info.cid,
            "source": source,
            "english_hint": english_hint,
        }
        # 附加结构渲染 URL
        if info.smiles:
            result["render_url"] = build_render_url(
                info.smiles,
                name=info.iupac_name or original_query,
                formula=info.molecular_formula,
                weight=str(info.molecular_weight) if info.molecular_weight else None,
            )
            result["svg_url"] = build_svg_url(info.smiles)
        return result

    @staticmethod
    def _chinese_to_english(chinese: str) -> Optional[str]:
        """常见中文化学名→英文映射（内置高频词典，避免 LLM 调用）"""
        mapping = {
            "水": "water", "酒精": "ethanol", "乙醇": "ethanol",
            "甲醇": "methanol", "丙酮": "acetone", "苯": "benzene",
            "甲苯": "toluene", "苯甲酸": "benzoic acid", "乙酸": "acetic acid",
            "盐酸": "hydrochloric acid", "硫酸": "sulfuric acid",
            "硝酸": "nitric acid", "氢氧化钠": "sodium hydroxide",
            "氢氧化钾": "potassium hydroxide", "氯化钠": "sodium chloride",
            "碳酸钙": "calcium carbonate", "碳酸钠": "sodium carbonate",
            "葡萄糖": "glucose", "蔗糖": "sucrose", "淀粉": "starch",
            "尿素": "urea", "阿司匹林": "aspirin", "咖啡因": "caffeine",
            "尼古丁": "nicotine", "乙醚": "diethyl ether",
            "氯仿": "chloroform", "乙酸乙酯": "ethyl acetate",
            "苯酚": "phenol", "甲醛": "formaldehyde", "乙醛": "acetaldehyde",
            "乙炔": "acetylene", "乙烯": "ethylene", "丙烯": "propylene",
            "环己烷": "cyclohexane", "萘": "naphthalene", "蒽": "anthracene",
            "吡啶": "pyridine", "呋喃": "furan", "噻吩": "thiophene",
            "吲哚": "indole", "嘌呤": "purine", "嘧啶": "pyrimidine",
        }
        # 精确匹配
        if chinese in mapping:
            return mapping[chinese]
        # 去掉"酸"后缀等常见变体
        clean = chinese.rstrip("溶液固体气体液体")
        if clean in mapping:
            return mapping[clean]
        return None
