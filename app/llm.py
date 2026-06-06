"""LLM 服务封装。

封装 OpenAI 兼容接口调用，提供：
- 自动重试（指数退避）
- JSON 输出模式
- Markdown 代码块清理
"""

import json
import logging
from typing import Any

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """LLM 调用异常。"""


class LLM:
    """LLM 服务。

    Usage:
        llm = LLM(api_key="xxx", base_url="https://...", model="milm")
        text = llm.chat("你好")
        data = llm.chat_json("返回 JSON: {{\"name\": \"张三\"}}")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.xiaomi.com/v1",
        model: str = "milm",
        temperature: float = 0.7,
        max_tokens: int = 16000,
    ) -> None:
        if not api_key:
            raise LLMError("API key 未配置")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        logger.info(f"LLM 初始化: model={model}, base_url={base_url}")

    @retry(
        retry=retry_if_exception_type((APIError, APITimeoutError, RateLimitError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    def chat(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        """调用 LLM，返回文本。

        Args:
            prompt: 用户消息。
            system: 系统提示词。
            json_mode: 是否启用 JSON 输出模式。
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content is None:
            raise LLMError("模型返回空内容")
        return content

    def chat_json(self, prompt: str, system: str = "") -> dict:
        """调用 LLM，返回解析后的 JSON。

        自动清理 Markdown 代码块标记。
        """
        raw = self.chat(
            prompt,
            system=system or "You are a professional assistant. Always respond with valid JSON.",
            json_mode=True,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # 尝试清理 markdown 代码块
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                cleaned = "\n".join(lines)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                raise LLMError(f"JSON 解析失败: {e}\n原始响应: {raw[:500]}") from e
