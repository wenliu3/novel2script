"""YAML 导出器。

将 Pydantic 数据模型序列化为 YAML 格式文件。
"""

import logging
from pathlib import Path

import yaml

from app.schema.script import Script
from app.utils.file_utils import ensure_dir

logger = logging.getLogger(__name__)


class CustomDumper(yaml.SafeDumper):
    """自定义 YAML Dumper，支持中文友好输出。"""

    pass


def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    """字符串表示器：多行文本使用 | 块格式。"""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


CustomDumper.add_representer(str, _str_representer)


def export_yaml(
    script: Script,
    output_dir: Path,
    filename: str = "script.yaml",
) -> Path:
    """将 Script 对象导出为 YAML 文件。

    Args:
        script: 脚本数据对象。
        output_dir: 输出目录。
        filename: 输出文件名。

    Returns:
        输出文件路径。
    """
    ensure_dir(output_dir)
    output_path = output_dir / filename

    # Pydantic model → dict → YAML
    data = script.model_dump(mode="json", exclude_none=True, exclude_defaults=False)

    yaml_content = yaml.dump(
        data,
        Dumper=CustomDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )

    output_path.write_text(yaml_content, encoding="utf-8")
    logger.info(f"YAML 已导出: {output_path}")

    return output_path
