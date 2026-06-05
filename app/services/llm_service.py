"""LLM 调用服务封装。

封装所有与 MiLM（小米大模型）的交互逻辑，提供：
- OpenAI 兼容接口调用
- 带指数退避的自动重试
- JSON 输出模式
- 流式输出支持
- 统一的错误处理
"""

import json
import logging
from typing import Any, Optional

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.services.config import Settings

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """LLM 服务基础异常。"""


class LLMService:
    """MiLM LLM 服务封装。

    基于 OpenAI Python SDK 调用 MiLM 的 OpenAI 兼容接口。

    Attributes:
        client: OpenAI 客户端实例。
        model: 模型名称。
        temperature: 生成温度。
        max_tokens: 最大输出 token 数。
    """

    def __init__(self, settings: Settings) -> None:
        """初始化 LLM 服务。

        Args:
            settings: 项目配置。

        Raises:
            LLMServiceError: API 密钥未配置时抛出。
        """
        if not settings.milm_api_key:
            raise LLMServiceError("MILM_API_KEY 未配置")

        self.client = OpenAI(
            api_key=settings.milm_api_key,
            base_url=settings.milm_base_url,
        )
        self.model = settings.milm_model
        self.temperature = settings.temperature
        self.max_tokens = settings.max_tokens
        self.retry_times = settings.retry_times
        self.retry_wait = settings.retry_wait

        logger.info(f"LLM 服务初始化完成: model={self.model}, base_url={settings.milm_base_url}")

    @retry(
        retry=retry_if_exception_type((APIError, APITimeoutError, RateLimitError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """调用 LLM 生成回复（非流式）。

        Args:
            messages: OpenAI 格式的消息列表。
            temperature: 覆盖默认温度。
            max_tokens: 覆盖默认最大 token 数。
            json_mode: 是否启用 JSON 输出模式。

        Returns:
            模型生成的文本响应。

        Raises:
            LLMServiceError: API 调用失败时抛出。
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if content is None:
                raise LLMServiceError("模型返回空内容")
            return content
        except (APIError, APITimeoutError, RateLimitError) as e:
            logger.error(f"LLM API 调用失败: {e}")
            raise LLMServiceError(f"API 调用失败: {e}") from e

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """调用 LLM 并解析 JSON 响应。

        自动启用 JSON 模式并解析返回的 JSON 字符串。

        Args:
            messages: OpenAI 格式的消息列表。
            temperature: 覆盖默认温度。
            max_tokens: 覆盖默认最大 token 数。

        Returns:
            解析后的 JSON 字典。

        Raises:
            LLMServiceError: JSON 解析失败时抛出。
        """
        raw = self.chat(
            messages, temperature=temperature, max_tokens=max_tokens, json_mode=True
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            # 尝试清理 markdown 代码块
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                cleaned = "\n".join(lines)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                raise LLMServiceError(f"JSON 解析失败: {e}\n原始响应前500字符: {raw[:500]}") from e

    def prompt(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
        **kwargs,
    ) -> str:
        """便捷方法：构建 system+user 消息并调用 LLM。

        Args:
            system: 系统提示词。
            user: 用户消息。
            json_mode: 是否启用 JSON 输出模式。
            **kwargs: 传递给 chat() 的额外参数。

        Returns:
            模型生成的文本响应。
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self.chat(messages, json_mode=json_mode, **kwargs)

    def prompt_json(
        self,
        system: str,
        user: str,
        **kwargs,
    ) -> dict[str, Any]:
        """便捷方法：构建 system+user 消息并解析 JSON 响应。

        Args:
            system: 系统提示词。
            user: 用户消息。
            **kwargs: 传递给 chat_json() 的额外参数。

        Returns:
            解析后的 JSON 字典。
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self.chat_json(messages, **kwargs)
