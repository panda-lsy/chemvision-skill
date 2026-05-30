"""SMILES → SVG 分子结构渲染器

使用 RDKit 将 SMILES 字符串渲染为 SVG 矢量图。
RDKit 是化学信息学标准库，广泛用于分子可视化。
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# RDKit 延迟导入（可选依赖）
_rdkit_available: Optional[bool] = None


def _check_rdkit() -> bool:
    """检查 RDKit 是否可用（缓存结果）"""
    global _rdkit_available
    if _rdkit_available is None:
        try:
            from rdkit import Chem  # noqa: F401
            from rdkit.Chem import Draw  # noqa: F401
            _rdkit_available = True
            logger.info("RDKit 可用，SVG 渲染已启用")
        except ImportError:
            _rdkit_available = False
            logger.warning("RDKit 未安装，SVG 渲染不可用。安装：pip install rdkit")
    return _rdkit_available


def smiles_to_svg(
    smiles: str,
    width: int = 350,
    height: int = 300,
    include_atom_indices: bool = False,
) -> Optional[str]:
    """将 SMILES 字符串渲染为 SVG 字符串

    Args:
        smiles: SMILES 字符串
        width: 图片宽度（像素）
        height: 图片高度（像素）
        include_atom_indices: 是否显示原子编号

    Returns:
        SVG 字符串，失败返回 None
    """
    if not smiles or not smiles.strip():
        return None

    if not _check_rdkit():
        return None

    try:
        from rdkit import Chem
        from rdkit.Chem import Draw, AllChem

        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is None:
            logger.warning(f"RDKit 无法解析 SMILES: {smiles}")
            return None

        # 计算 2D 坐标
        AllChem.Compute2DCoords(mol)

        # 生成 SVG
        drawer = Draw.MolDraw2DSVG(width, height)
        opts = drawer.drawOptions()
        opts.addAtomIndices = include_atom_indices
        opts.bondLineWidth = 1.5
        opts.fixedFontSize = 12

        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()

        return svg

    except Exception as e:
        logger.error(f"SMILES→SVG 渲染失败: {e}", exc_info=True)
        return None


def smiles_to_svg_base64(smiles: str, width: int = 350, height: int = 300) -> Optional[str]:
    """将 SMILES 渲染为 base64 编码的 SVG（用于 data URI 嵌入）"""
    import base64
    svg = smiles_to_svg(smiles, width, height)
    if svg is None:
        return None
    return base64.b64encode(svg.encode("utf-8")).decode("ascii")


def is_rdkit_available() -> bool:
    """检查 RDKit 是否可用"""
    return _check_rdkit()
