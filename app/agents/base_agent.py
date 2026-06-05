"""Agent 基类。

所有处理 Agent 的抽象基类，提供：
- 统一的 LLM 调用接口
- 提示词加载机制
- 日志记录
- 执行耗时统计
"""

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from string import Formatter
from typing import Any

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# 提示词模板目录
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class _SafeDict(dict):
    """安全字典：未找到的键返回 {key} 原始文本。"""

    def __missing__(self, key):
        return "{" + key + "}"


class BaseAgent(ABC):
    """Agent 抽象基类。

    所有具体 Agent 必须实现 execute() 方法。

    Attributes:
        name: Agent 名称（用于日志和调试）。
        llm: LLM 服务实例。
    """

    def __init__(self, name: str, llm: LLMService) -> None:
        self.name = name
        self.llm = llm
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行 Agent 的核心逻辑。子类必须实现。

        Returns:
            Agent 的处理结果。
        """
        ...

    def run(self, **kwargs) -> Any:
        """运行 Agent，包含计时和错误处理。

        调用 execute() 并记录执行时间、处理异常。

        Returns:
            Agent 的处理结果。

        Raises:
            Exception: 重新抛出 execute() 中的异常。
        """
        self.logger.info(f"▶ 开始执行: {self.name}")
        start = time.time()

        try:
            result = self.execute(**kwargs)
            elapsed = time.time() - start
            self.logger.info(f"✓ 完成: {self.name} ({elapsed:.1f}s)")
            return result
        except Exception as e:
            elapsed = time.time() - start
            self.logger.error(f"✗ 失败: {self.name} ({elapsed:.1f}s) - {e}")
            raise

    def load_prompt(self, name: str) -> str:
        """加载提示词模板文件。

        从 prompts/ 目录读取 .md 文件作为提示词模板。

        Args:
            name: 提示词文件名（不含 .md 后缀）。

        Returns:
            提示词模板文本。

        Raises:
            FileNotFoundError: 提示词文件不存在时抛出。
        """
        prompt_file = PROMPTS_DIR / f"{name}.md"
        if not prompt_file.exists():
            raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
        content = prompt_file.read_text(encoding="utf-8").strip()
        # 去除 YAML front matter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        return content

    def render_prompt(self, template: str, **variables: str) -> str:
        """安全渲染提示词模板。

        使用 SafeDict 避免缺失变量时报错。

        Args:
            template: 包含 {variable} 占位符的模板。
            **variables: 要替换的变量。

        Returns:
            渲染后的提示词。
        """
        return template.format_map(_SafeDict(variables))

    def llm_prompt(self, prompt_name: str, user_content: str, **extra_vars) -> str:
        """快捷方法：加载提示词 → 渲染 → 调用 LLM → 返回文本。

        Args:
            prompt_name: 提示词文件名。
            user_content: 用户消息内容（通常是待处理的文本）。
            **extra_vars: 额外的模板变量。

        Returns:
            LLM 生成的文本响应。
        """
        template = self.load_prompt(prompt_name)
        rendered = self.render_prompt(template, user_content=user_content, **extra_vars)
        system = f"You are a professional assistant helping with novel-to-script conversion."
        return self.llm.prompt(system, rendered)

    def llm_prompt_json(self, prompt_name: str, user_content: str, **extra_vars) -> dict:
        """快捷方法：加载提示词 → 渲染 → 调用 LLM → 返回 JSON。

        Args:
            prompt_name: 提示词文件名。
            user_content: 用户消息内容。
            **extra_vars: 额外的模板变量。

        Returns:
            LLM 生成的 JSON 字典。
        """
        template = self.load_prompt(prompt_name)
        rendered = self.render_prompt(template, user_content=user_content, **extra_vars)
        system = f"You are a professional assistant. Always respond with valid JSON."
        return self.llm.prompt_json(system, rendered)
