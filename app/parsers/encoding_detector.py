"""文件编码自动检测模块。

中文网络小说文件编码多样（UTF-8、GBK、GB2312、BIG5 等），
本模块提供编码自动检测能力，确保正确读取所有中文文本。

优先使用 chardet 库检测，检测失败时按常见编码逐个尝试。
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 中文小说最常见的编码，按优先级排列
COMMON_ENCODINGS = [
    "utf-8",
    "utf-8-sig",       # Windows 带 BOM 的 UTF-8
    "gbk",             # 简体中文（兼容 GB2312）
    "gb18030",         # GBK 超集，覆盖更多字符
    "gb2312",          # 早期简体中文编码
    "big5",            # 繁体中文
    "latin-1",         # 兜底（不会抛异常，但中文会乱码）
]


def detect_encoding(file_path: Path) -> str:
    """自动检测文件编码。

    检测策略：
    1. 检查 BOM（字节序标记）头
    2. 使用 chardet 库分析（如果安装了）
    3. 逐个尝试常见编码，检查是否能正确解码

    Args:
        file_path: 文件路径。

    Returns:
        检测到的编码名称。

    Raises:
        ValueError: 所有编码尝试均失败时抛出。
    """
    raw_bytes = file_path.read_bytes()

    if not raw_bytes:
        raise ValueError(f"文件为空: {file_path}")

    # ── 策略1: BOM 检测 ──
    bom_encoding = _check_bom(raw_bytes)
    if bom_encoding:
        logger.debug(f"BOM 检测: {file_path.name} → {bom_encoding}")
        return bom_encoding

    # ── 策略2: chardet 检测 ──
    chardet_encoding = _chardet_detect(raw_bytes)
    if chardet_encoding:
        # 验证 chardet 结果是否真的能正确解码
        if _can_decode(raw_bytes, chardet_encoding):
            logger.debug(f"chardet 检测: {file_path.name} → {chardet_encoding}")
            return chardet_encoding

    # ── 策略3: 逐个尝试常见编码 ──
    for enc in COMMON_ENCODINGS:
        if _can_decode(raw_bytes, enc):
            logger.debug(f"逐个尝试: {file_path.name} → {enc}")
            return enc

    raise ValueError(
        f"无法检测文件编码: {file_path}\n"
        f"文件大小: {len(raw_bytes)} 字节"
    )


def read_with_auto_encoding(file_path: Path) -> tuple[str, str]:
    """自动检测编码并读取文件内容。

    Args:
        file_path: 文件路径。

    Returns:
        (编码名称, 文件内容) 元组。

    Raises:
        FileNotFoundError: 文件不存在时抛出。
        ValueError: 编码检测失败或文件为空时抛出。
    """
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    encoding = detect_encoding(file_path)
    content = file_path.read_text(encoding=encoding).strip()

    if not content:
        raise ValueError(f"文件为空: {file_path}")

    return encoding, content


def _check_bom(raw_bytes: bytes) -> str | None:
    """检查 BOM (Byte Order Mark) 头。"""
    bom_map = [
        (b"\xef\xbb\xbf", "utf-8-sig"),
        (b"\xff\xfe", "utf-16-le"),
        (b"\xfe\xff", "utf-16-be"),
        (b"\xff\xfe\x00\x00", "utf-32-le"),
        (b"\x00\x00\xfe\xff", "utf-32-be"),
    ]
    for bom, encoding in bom_map:
        if raw_bytes.startswith(bom):
            return encoding
    return None


def _chardet_detect(raw_bytes: bytes) -> str | None:
    """使用 chardet 库检测编码（可选依赖）。"""
    try:
        import chardet

        result = chardet.detect(raw_bytes)
        if result and result.get("encoding") and result.get("confidence", 0) > 0.5:
            return result["encoding"]
    except ImportError:
        pass  # chardet 未安装，跳过
    return None


def _can_decode(raw_bytes: bytes, encoding: str) -> bool:
    """测试字节数据是否能用指定编码正确解码。"""
    try:
        decoded = raw_bytes.decode(encoding)
        # 检查解码后是否有足够的中文字符（排除 latin-1 误判）
        chinese_chars = sum(1 for c in decoded if "一" <= c <= "鿿")
        # 如果中文字符占比太低且不是 latin-1，可能不是正确编码
        if chinese_chars < len(decoded) * 0.01 and encoding != "latin-1":
            return False
        return True
    except (UnicodeDecodeError, LookupError):
        return False
