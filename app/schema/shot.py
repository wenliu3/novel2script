"""镜头数据模型。

镜头相关的辅助类型定义。
注：核心 Shot 和 DialogueLine 已在 scene.py 中定义，
此模块提供额外的镜头辅助工具。
"""

from app.schema.scene import Shot, DialogueLine

__all__ = ["Shot", "DialogueLine"]
