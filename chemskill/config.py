"""ChemVision Skill 配置管理"""

import os
from pathlib import Path
from dataclasses import dataclass, field

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class SkillConfig:
    """全局配置"""

    # Ollama
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen3.6-35b-a3b")
    )

    # FastAPI 服务
    server_host: str = field(
        default_factory=lambda: os.getenv("SERVER_HOST", "0.0.0.0")
    )
    server_port: int = field(
        default_factory=lambda: int(os.getenv("SERVER_PORT", "8899"))
    )

    # PubChem API
    pubchem_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"
    pubchem_timeout: float = 10.0
    pubchem_max_retries: int = 3

    # OPSIN API
    opsin_base_url: str = "https://opsin.ch.cam.ac.uk/opsin"
    opsin_timeout: float = 8.0

    # Agent
    max_tool_rounds: int = 5  # 最多工具调用轮数
    agent_temperature: float = 0.1  # 低温度保证化学准确性

    def load_system_prompt(self) -> str:
        """加载 Agent 系统提示词"""
        prompt_file = PROMPTS_DIR / "system.txt"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return self._default_system_prompt()

    def load_tool_guidance(self) -> str:
        """加载工具调用指导"""
        guidance_file = PROMPTS_DIR / "tool_guidance.txt"
        if guidance_file.exists():
            return guidance_file.read_text(encoding="utf-8")
        return ""

    @staticmethod
    def _default_system_prompt() -> str:
        return (
            "你是一位专业的 AI 化学家助手（ChemVision Agent）。"
            "你的核心能力是通过调用真实的化学数据库工具来回答化学问题，"
            "而不是仅凭自身记忆生成答案。\n\n"
            "## 能力\n"
            "- 查询化学名称对应的分子结构（SMILES、分子式、分子量）\n"
            "- 解析 SMILES 字符串获取化学信息\n"
            "- 查询化学品安全信息和危险标识\n"
            "- 推测化学反应方程式和条件\n"
            "- 从化学结构图片中识别化合物\n\n"
            "## 原则\n"
            "1. 优先使用工具查询，避免凭记忆编造化学数据\n"
            "2. 查询不到时如实告知，不伪造结果\n"
            "3. 用中文回答，专业术语保留英文原文\n"
            "4. 展示完整的化学信息：SMILES、分子式、分子量\n"
        )


# 全局配置实例
config = SkillConfig()
