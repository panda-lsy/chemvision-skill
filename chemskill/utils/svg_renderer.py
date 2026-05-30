"""SMILES → 结构图渲染工具

使用 smiles-drawer.js（ChemVision 同款轻量 JS 库）渲染分子结构。
提供两种渲染方式：
- /render?smiles=xxx  — 完整渲染页面（含化学信息）
- /api/svg/{smiles}   — 纯结构图（可截图/嵌入）
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote as url_quote


def build_render_url(
    smiles: str,
    base_url: str = "http://localhost:8899",
    name: Optional[str] = None,
    formula: Optional[str] = None,
    weight: Optional[str] = None,
) -> Optional[str]:
    """构建完整渲染页面 URL（含化学信息卡片）"""
    if not smiles or not smiles.strip():
        return None
    params = f"smiles={url_quote(smiles.strip())}"
    if name:
        params += f"&name={url_quote(name)}"
    if formula:
        params += f"&formula={url_quote(formula)}"
    if weight:
        params += f"&weight={url_quote(str(weight))}"
    return f"{base_url}/render?{params}"


def build_svg_url(
    smiles: str,
    base_url: str = "http://localhost:8899",
) -> Optional[str]:
    """构建纯结构图 URL（适合截图/嵌入）"""
    if not smiles or not smiles.strip():
        return None
    return f"{base_url}/api/svg/{url_quote(smiles.strip())}"
