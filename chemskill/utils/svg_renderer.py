"""SMILES → 结构图渲染工具

使用 smiles-drawer.js（ChemVision 同款轻量 JS 库）渲染分子结构。
不依赖 RDKit，纯前端渲染，通过 FastAPI /render 页面展示。
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
    """构建分子结构渲染页面 URL

    Args:
        smiles: SMILES 字符串
        base_url: 服务基础地址
        name: 化学名称（可选，展示用）
        formula: 分子式（可选）
        weight: 分子量（可选）

    Returns:
        渲染页面 URL，SMILES 为空时返回 None
    """
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
