"""ChemVision Skill 配置管理"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SkillConfig:
    """全局配置"""

    # FastAPI 服务
    server_host: str = field(
        default_factory=lambda: os.getenv("SERVER_HOST", "0.0.0.0")
    )
    server_port: int = field(
        default_factory=lambda: int(os.getenv("SERVER_PORT", "8899"))
    )

    # Ollama（供 reaction_predict / ocr_chemistry 工具使用）
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen3.6-35b-a3b")
    )

    # PubChem API
    pubchem_timeout: float = 10.0
    pubchem_max_retries: int = 3

    # OPSIN API
    opsin_timeout: float = 8.0


# 全局配置实例
config = SkillConfig()
