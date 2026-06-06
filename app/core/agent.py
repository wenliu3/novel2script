"""ScriptAgent — 唯一调 LLM 的类。

每个章节独立调用一次 LLM，输出完整 YAML 剧本。
"""

from __future__ import annotations

import logging
import re

import yaml

from app.llm import LLM
from app.models import Screenplay, fix_llm_data

logger = logging.getLogger(__name__)

# ── 提示词模板 ─────────────────────────────────────────────

SYSTEM_PROMPT = """\
你是剧本改编助手。将小说文本转为 YAML 剧本。

【严格输出规则】
1. 只输出合法 YAML，不要任何解释、注释、markdown 标记
2. 每个 scene 必须包含以下字段，一个都不能少：
   - scene_number（整数）
   - heading（字符串，格式："内景/外景 地点 - 时间"）
   - int_ext（"内景" 或 "外景"）
   - location（地点名称）
   - time_of_day（如：白天、夜晚、黄昏、清晨）
   - content（列表，由 action 和 dialogue 交替组成）
3. 每个 chapter 必须有 title 字段
4. 顶层必须有 title 字段
5. content 中每个 item 必须有 type 字段（"action" 或 "dialogue"）和 text 字段
6. 不要用 title 代替 heading，不要用 description 代替 content
"""

CHUNK_TEMPLATE = """\
将以下小说转为 YAML 剧本。严格按下面的格式输出，字段名不能改：

title: "剧本标题"
author: "作者"
genre: "类型"
characters:
  角色名: "简介"
chapters:
  - chapter_number: 1
    title: "章节标题"
    scenes:
      - scene_number: 1
        heading: "内景 客栈 - 白天"
        int_ext: "内景"
        location: "客栈"
        time_of_day: "白天"
        characters: ["角色A"]
        summary: "一句话概括"
        content:
          - type: action
            text: "动作描述"
          - type: dialogue
            character: "角色A"
            text: "对白内容"

【注意】
- heading、int_ext、location、time_of_day、content 每个 scene 都必须有
- content 是列表，每项必须有 type 和 text
- 不要输出 ```yaml 标记
- 每段原文只输出 1 个 chapter，不要自行拆分成多个 chapter
- chapters 列表里只有 1 个元素

{chapter_instruction}

以下是小说原文：
---
{novel_text}
---
"""


def _chapter_instruction(text: str) -> str:
    """根据文本是否有章节标记，返回不同的章节处理指令。"""
    from app.core.splitter import has_chapter_structure
    if has_chapter_structure(text):
        return "这段原文是一个完整章节，请输出为 1 个 chapter，保留原标题，不要拆分。"
    return "这段原文没有章节标记，请输出为 1 个 chapter，标题用「第一部分」。"


def _fix_yaml_text(text: str) -> str:
    """修复 LLM 输出的 YAML 常见问题。"""
    text = text.replace("\t", "  ")
    # 中文冒号 → 英文冒号 + 空格
    text = re.sub(r"^(.+?)：(\s*)", r"\1: ", text, flags=re.MULTILINE)
    return text


def _try_parse_yaml(text: str) -> dict | None:
    """尝试多种方式解析 YAML。"""
    # 方式 1：直接解析
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 方式 2：修复缩进后解析
    fixed = _fix_yaml_text(text)
    try:
        data = yaml.safe_load(fixed)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # 方式 3：尝试提取第一个有效的 YAML 块
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("title") or line.strip().startswith("chapters"):
            try:
                data = yaml.safe_load("\n".join(lines[i:]))
                if isinstance(data, dict):
                    return data
            except Exception:
                continue

    return None


def _strip_yaml_fence(text: str) -> str:
    """清理 LLM 输出中可能的 markdown 代码块包裹和多余内容。"""
    text = text.strip()

    if "```" in text:
        lines = text.split("\n")
        start, end = None, None
        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                if start is None:
                    start = i
                end = i
        if start is not None and end is not None and start != end:
            lines = lines[start + 1:end]
            text = "\n".join(lines)

    # 去掉开头的非 YAML 行
    lines = text.split("\n")
    yaml_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and (": " in stripped or stripped.endswith(":") or stripped.startswith("-")):
            yaml_start = i
            break
    if yaml_start > 0:
        lines = lines[yaml_start:]
        text = "\n".join(lines)

    return text.strip()


class ScriptAgent:
    """唯一 Agent，负责所有 LLM 调用。

    每个章节独立处理，无上下文依赖。

    Usage:
        agent = ScriptAgent(llm)
        yaml_str = agent.convert_chunk(text, chapter_title="第001章 标题")
    """

    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    def convert_chunk(self, text: str, chapter_title: str = "") -> str:
        """将一个文本块转换为 YAML 剧本。

        如果首次输出 YAML 校验失败，会自动重试一次。
        """
        ch_inst = _chapter_instruction(text)

        title_inst = ""
        if chapter_title:
            title_inst = f'\n原文章节标题是「{chapter_title}」，请务必使用这个标题作为 chapter 的 title 字段。'

        prompt = CHUNK_TEMPLATE.format(
            chapter_instruction=ch_inst + title_inst,
            novel_text=text,
        )

        logger.info(f"调用 LLM（{len(text):,} 字符）")
        raw = self.llm.chat(prompt, system=SYSTEM_PROMPT)
        yaml_str = _strip_yaml_fence(raw)

        # 校验，失败则重试一次
        _, err = self.validate_screenplay(yaml_str)
        if err:
            logger.warning(f"首次输出 YAML 无效: {err}，重试...")
            fix_prompt = (
                f"以下 YAML 有语法错误，请修正后重新输出完整的 YAML（不要加任何解释）：\n"
                f"错误信息: {err}\n\n"
                f"原始 YAML:\n{yaml_str[:3000]}"
            )
            try:
                raw2 = self.llm.chat(fix_prompt, system=SYSTEM_PROMPT)
                yaml_str2 = _strip_yaml_fence(raw2)
                _, err2 = self.validate_screenplay(yaml_str2)
                if not err2:
                    yaml_str = yaml_str2
                    logger.info("重试成功")
                else:
                    logger.warning(f"重试仍然失败: {err2}，使用原始输出")
            except Exception as e:
                logger.warning(f"重试异常: {e}，使用原始输出")

        logger.info(f"LLM 返回 {len(yaml_str):,} 字符 YAML")
        return yaml_str

    @staticmethod
    def validate_screenplay(yaml_str: str) -> tuple[Screenplay | None, str | None]:
        """校验 YAML 字符串，自动修复常见格式问题。"""
        data = _try_parse_yaml(yaml_str)
        if not data:
            return None, "YAML 解析失败"
        try:
            data = fix_llm_data(data)
            if not data.get("chapters"):
                return None, "缺少 chapters 字段"
            screenplay = Screenplay(**data)
            return screenplay, None
        except Exception as e:
            return None, str(e)
