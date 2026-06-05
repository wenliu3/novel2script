"""配置管理模块。

通过环境变量和 .env 文件加载项目配置，提供统一的配置访问接口。
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass
class Settings:
    """项目全局配置。

    Attributes:
        milm_api_key: MiLM API 密钥。
        milm_base_url: MiLM API 端点（OpenAI 兼容接口）。
        milm_model: MiLM 模型名称。
        output_base: 输出文件根目录。
        retry_times: API 调用最大重试次数。
        retry_wait: 重试间隔基数（秒）。
        temperature: 生成温度 (0.0-1.0)。
        max_tokens: 单次调用最大输出 token 数。
    """

    milm_api_key: str = ""
    milm_base_url: str = "https://api.xiaomi.com/v1"
    milm_model: str = "milm"
    output_base: Path = field(default_factory=lambda: Path("output"))
    retry_times: int = 3
    retry_wait: float = 1.0
    temperature: float = 0.7
    max_tokens: int = 4096

    def validate(self) -> list[str]:
        """验证配置完整性，返回错误列表（空列表表示通过）。"""
        errors = []
        if not self.milm_api_key:
            errors.append("未找到 MILM_API_KEY。请在 .env 文件或环境变量中配置。")
        if not 0.0 <= self.temperature <= 1.0:
            errors.append(f"temperature 必须在 0.0-1.0 之间，当前值: {self.temperature}")
        if self.max_tokens < 256:
            errors.append(f"max_tokens 不能小于 256，当前值: {self.max_tokens}")
        return errors


def load_settings(**overrides) -> Settings:
    """从环境变量加载配置，支持关键字参数覆盖。

    Args:
        **overrides: 覆盖默认配置的键值对。

    Returns:
        配置好的 Settings 实例。

    Raises:
        ValueError: 配置验证失败时抛出。
    """
    settings = Settings(
        milm_api_key=overrides.get("milm_api_key") or os.getenv("MILM_API_KEY", ""),
        milm_base_url=overrides.get("milm_base_url") or os.getenv(
            "MILM_BASE_URL", "https://api.xiaomi.com/v1"
        ),
        milm_model=overrides.get("milm_model") or os.getenv("MILM_MODEL", "milm"),
        output_base=Path(overrides.get("output_base") or os.getenv("OUTPUT_BASE", "output")),
        retry_times=int(overrides.get("retry_times", 3)),
        retry_wait=float(overrides.get("retry_wait", 1.0)),
        temperature=float(overrides.get("temperature", 0.7)),
        max_tokens=int(overrides.get("max_tokens", 4096)),
    )

    errors = settings.validate()
    if errors:
        raise ValueError("配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors))

    return settings
