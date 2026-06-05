"""流水线编排器。

协调所有 Agent 的执行顺序，管理数据在 Agent 间的传递，
处理异常和重试，记录整体处理进度。
"""

import logging
import time
from pathlib import Path

from app.agents.chapter_agent import ChapterAgent
from app.agents.character_agent import CharacterAgent
from app.agents.dialogue_agent import DialogueAgent
from app.agents.scene_agent import SceneAgent
from app.agents.validator_agent import ValidationResult, ValidatorAgent
from app.agents.yaml_builder import YAMLBuilderAgent
from app.exporters.yaml_exporter import export_yaml
from app.schema.character import CharacterList
from app.schema.script import Script
from app.services.config import Settings
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class Orchestrator:
    """流水线编排器。

    按顺序调用各 Agent，管理数据流转：

    chapter_agent → character_agent → [scene_agent → dialogue_agent] × N章
    → yaml_builder → validator → yaml_exporter

    Attributes:
        settings: 项目配置。
        llm: LLM 服务实例。
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm = LLMService(settings)

        # 初始化所有 Agent
        self.chapter_agent = ChapterAgent(self.llm)
        self.character_agent = CharacterAgent(self.llm)
        self.scene_agent = SceneAgent(self.llm)
        self.dialogue_agent = DialogueAgent(self.llm)
        self.yaml_builder = YAMLBuilderAgent(self.llm)
        self.validator = ValidatorAgent(self.llm)

    def run(self, novel_dir: Path, chapters: list[int] | None = None) -> Script:
        """执行完整的转换流水线。

        Args:
            novel_dir: 小说根目录。
            chapters: 要处理的章节编号列表，None 表示处理所有。

        Returns:
            生成的完整 Script 对象。
        """
        start_time = time.time()
        logger.info(f"{'='*50}")
        logger.info(f"开始处理: {novel_dir.name}")
        logger.info(f"{'='*50}")

        # ── Step 1: 解析章节 ──
        all_chapters = self.chapter_agent.run(novel_dir=novel_dir)

        # 过滤指定章节
        if chapters:
            all_chapters = [ch for ch in all_chapters if ch.number in chapters]
            logger.info(f"筛选后: {len(all_chapters)} 个章节")

        if not all_chapters:
            logger.warning("没有要处理的章节")
            return Script()

        # ── Step 2: 提取角色（合并所有章节文本） ──
        full_text = "\n\n".join(
            f"=== 第{ch.number}章 ===\n{ch.raw_text}" for ch in all_chapters
        )
        characters = self.character_agent.run(chapters_text=full_text)
        logger.info(f"提取到 {len(characters.characters)} 个角色")

        # ── Step 3: 逐章处理（场景拆分 + 对话翻译） ──
        chapter_scripts = []
        for ch in all_chapters:
            logger.info(f"── 处理第{ch.number}章 ──")

            # 拆分场景
            scenes = self.scene_agent.run(
                chapter_text=ch.raw_text,
                chapter_number=ch.number,
                character_names=[c.name for c in characters.characters],
            )

            # 为每个场景生成镜头和对话
            for i, scene in enumerate(scenes):
                scene = self.dialogue_agent.run(
                    scene=scene,
                    chapter_text=ch.raw_text,
                    chapter_number=ch.number,
                    character_names=[c.name for c in characters.characters],
                )
                scenes[i] = scene

            chapter_scripts.append((ch.number, ch.title, scenes))

        # ── Step 4: 组装 YAML 结构 ──
        script = self.yaml_builder.run(
            novel_name=novel_dir.name,
            chapter_scripts=chapter_scripts,
        )

        # ── Step 5: 校验 ──
        validation = self.validator.run(script=script)
        if not validation.is_valid:
            logger.error(f"校验失败: {validation.summary()}")
            for err in validation.errors:
                logger.error(f"  ✗ {err}")
        if validation.warnings:
            for warn in validation.warnings:
                logger.warning(f"  ⚠ {warn}")

        # ── Step 6: 导出 YAML ──
        output_path = self.settings.output_base / novel_dir.name
        export_yaml(script, output_path, f"{novel_dir.name}_script.yaml")

        elapsed = time.time() - start_time
        logger.info(f"{'='*50}")
        logger.info(
            f"✓ 处理完成: {len(script.chapters)} 章, "
            f"{script.total_scenes()} 场景, "
            f"{script.total_shots()} 镜头 ({elapsed:.1f}s)"
        )
        logger.info(f"{'='*50}")

        return script
