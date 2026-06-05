"""章节文本解析器。

提供底层的文本解析功能，如正则切分、编码处理等。
"""

import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def split_paragraphs(text: str) -> list[str]:
    """将文本按段落分割。

    以连续空行为段落分隔符，过滤空段落。

    Args:
        text: 输入文本。

    Returns:
        段落列表。
    """
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if p.strip()]


def extract_dialogue(text: str) -> list[tuple[str, str]]:
    """从文本中提取对话（中文引号格式）。

    匹配格式：
    - "xxx" 或 「xxx」 或 "xxx"

    Args:
        text: 输入文本。

    Returns:
        [(说话人提示, 对话内容)] 列表。
        说话人可能为空字符串（未识别时）。
    """
    results = []

    # 匹配中文引号对话
    pattern = r'[""「」]([^""「」]+)[""「」]'
    for match in re.finditer(pattern, text):
        dialogue = match.group(1).strip()
        # 尝试从引号前获取说话人
        prefix = text[:match.start()].split("\n")[-1].strip()
        speaker = ""
        # 常见格式："XXX说："或"XXX道："
        speaker_match = re.search(r"([一-鿿]{1,5})(?:说|道|喊|问|答|笑|叹)", prefix)
        if speaker_match:
            speaker = speaker_match.group(1)

        results.append((speaker, dialogue))

    return results


def clean_text(text: str) -> str:
    """清理文本：去除多余空白、特殊字符。

    Args:
        text: 输入文本。

    Returns:
        清理后的文本。
    """
    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 去除行尾空白
    lines = [line.rstrip() for line in text.split("\n")]
    # 合并多余空行
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return cleaned.strip()
