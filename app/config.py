"""项目配置。"""

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class Settings:
    """项目配置。"""
    milm_api_key: str = ""
    milm_base_url: str = "https://api.xiaomi.com/v1"
    milm_model: str = "milm"
    temperature: float = 0.7
    max_tokens: int = 16000
    output_base: Path = field(default_factory=lambda: Path("output"))
    chunk_size: int = 100_000
    chunk_overlap: int = 5_000

    def validate(self) -> list[str]:
        errors = []
        if not self.milm_api_key:
            errors.append("未找到 MILM_API_KEY")
        if not 0.0 <= self.temperature <= 1.0:
            errors.append(f"temperature 必须在 0.0-1.0，当前: {self.temperature}")
        return errors


def load_settings(**overrides) -> Settings:
    """从环境变量加载配置。"""
    settings = Settings(
        milm_api_key=overrides.get("milm_api_key") or os.getenv("MILM_API_KEY", ""),
        milm_base_url=overrides.get("milm_base_url") or os.getenv("MILM_BASE_URL", "https://api.xiaomi.com/v1"),
        milm_model=overrides.get("milm_model") or os.getenv("MILM_MODEL", "milm"),
        temperature=float(overrides.get("temperature", os.getenv("TEMPERATURE", "0.7"))),
        max_tokens=int(overrides.get("max_tokens", os.getenv("MAX_TOKENS", "16000"))),
        output_base=Path(overrides.get("output_base") or os.getenv("OUTPUT_BASE", "output")),
        chunk_size=int(overrides.get("chunk_size", os.getenv("CHUNK_SIZE", "100000"))),
        chunk_overlap=int(overrides.get("chunk_overlap", os.getenv("CHUNK_OVERLAP", "5000"))),
    )
    errors = settings.validate()
    if errors:
        raise ValueError("配置错误:\n" + "\n".join(f"  - {e}" for e in errors))
    return settings


def setup_logging(verbose: bool = False) -> None:
    """配置全局日志。"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
