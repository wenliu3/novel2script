"""文件读写工具模块。

提供统一的文件操作接口，处理编码、路径等通用问题。
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_text_file(path: Path, encoding: str = "utf-8") -> str:
    """读取文本文件内容。

    Args:
        path: 文件路径。
        encoding: 文件编码，默认 utf-8。

    Returns:
        文件文本内容。

    Raises:
        FileNotFoundError: 文件不存在时抛出。
        ValueError: 文件为空时抛出。
    """
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    content = path.read_text(encoding=encoding).strip()
    if not content:
        raise ValueError(f"文件为空: {path}")

    return content


def write_text_file(path: Path, content: str, encoding: str = "utf-8") -> Path:
    """写入文本文件，自动创建父目录。

    Args:
        path: 文件路径。
        content: 要写入的文本内容。
        encoding: 文件编码，默认 utf-8。

    Returns:
        写入的文件路径。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)
    logger.info(f"已写入文件: {path}")
    return path


def ensure_dir(path: Path) -> Path:
    """确保目录存在，不存在则创建。

    Args:
        path: 目录路径。

    Returns:
        目录路径。
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
