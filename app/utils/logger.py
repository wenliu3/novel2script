"""日志配置模块。

提供统一的日志配置，所有模块通过此模块获取 logger 实例。
"""

import logging
import sys


def setup_logging(verbose: bool = False) -> None:
    """配置全局日志格式和级别。

    Args:
        verbose: 是否启用 DEBUG 级别日志。
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str) -> logging.Logger:
    """获取指定模块的 logger 实例。

    Args:
        name: 模块名称（通常传 __name__）。

    Returns:
        配置好的 Logger 实例。
    """
    return logging.getLogger(name)
