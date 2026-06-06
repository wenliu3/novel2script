"""Builder — YAML 导出（纯 Python，不调 LLM）。

将 Screenplay 对象导出为 YAML 文件。
key 用英文，value 用中文。
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from enum import Enum

from app.models import Screenplay

logger = logging.getLogger(__name__)


def export_yaml(screenplay: Screenplay, output_dir: Path, filename: str = "script.yaml") -> Path:
    """导出 YAML 文件（英文 key，中文 value）。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    data = screenplay.model_dump(mode="json", exclude_none=True, exclude_defaults=False)

    # 自定义 Dumper：多行用 | 块格式，枚举输出 value
    class _Dumper(yaml.SafeDumper):
        pass

    def _str_rep(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    def _enum_rep(dumper, data):
        return dumper.represent_scalar("tag:yaml.org,2002:str", data.value)

    def _none_rep(dumper, data):
        return dumper.represent_scalar("tag:yaml.org,2002:null", "")

    _Dumper.add_representer(str, _str_rep)
    _Dumper.add_representer(Enum, _enum_rep)
    _Dumper.add_representer(type(None), _none_rep)

    header = "# LRM 剧本 - 由 novel2script 生成\n\n"
    content = yaml.dump(
        data, Dumper=_Dumper, allow_unicode=True,
        default_flow_style=False, sort_keys=False, width=120,
    )
    output_path.write_text(header + content, encoding="utf-8")
    logger.info(f"YAML 已导出: {output_path}")
    return output_path
