"""YAML 构建 Agent（PR-07 核心模块）。

将所有上游 Agent 的输出组装为完整的 Script 数据结构：
- 聚合章节、场景、节拍、镜头
- 生成角色 ID 映射并应用到 beat 引用
- 可选 LLM 辅助生成标题和梗概
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agents.base_agent import BaseAgent
from app.schema.character import CharacterList
from app.schema.chapter import ChapterAnalysisReport
from app.schema.scene import Beat, Scene
from app.schema.script import ChapterScript, Script, ScriptCharacter, ScriptMetadata
from app.services.llm_service import LLMService


class YAMLBuilderAgent(BaseAgent):
    """YAML 构建 Agent。

    职责：
    1. 聚合章节、场景、节拍、镜头数据
    2. 构建角色 ID 映射表
    3. 规范化 beat 中的角色引用
    4. 可选 LLM 生成标题、梗概（logline）
    5. 统计并填充 metadata
    """

    def __init__(self, llm: LLMService) -> None:
        super().__init__("yaml_builder", llm)

    def execute(
        self,
        novel_name: str,
        chapter_scripts: list[tuple[int, str, list[Scene]]],
        characters: CharacterList | None = None,
        chapter_report: ChapterAnalysisReport | None = None,
        genre: str = "",
    ) -> Script:
        """组装完整的脚本结构。

        Args:
            novel_name: 小说名称。
            chapter_scripts: 每章的 (章节编号, 章节标题, 场景列表) 元组。
            characters: 角色列表（用于构建角色段）。
            chapter_report: 章节分析报告（用于生成 logline）。
            genre: 剧本类型。

        Returns:
            完整的 Script 对象。
        """
        # ── 构建角色 ID 映射 ──
        char_id_map: dict[str, str] = {}  # name → id
        script_characters: list[ScriptCharacter] = []
        if characters and characters.characters:
            # 按重要性排序
            sorted_chars = sorted(
                characters.characters,
                key=lambda c: c.importance,
                reverse=True,
            )
            for i, char in enumerate(sorted_chars):
                char_id = f"char_{i + 1:03d}"
                char_id_map[char.name] = char_id
                # 别名也映射到同一 ID
                for alias in char.aliases:
                    char_id_map[alias] = char_id
                # enum → 中文映射
                role_map = {
                    "protagonist": "主角", "antagonist": "反派",
                    "supporting": "重要配角", "minor": "配角", "mentioned": "龙套",
                }
                script_characters.append(
                    ScriptCharacter(
                        id=char_id,
                        name=char.name,
                        role=role_map.get(str(char.role.value) if hasattr(char.role, 'value') else str(char.role), "配角"),
                        traits=char.personality.split("，") if char.personality else [],
                        motivation=char.background[:80] if char.background else "",
                    )
                )

        # ── 规范化 beat 中的角色引用 ──
        for _, _, scenes in chapter_scripts:
            for scene in scenes:
                for beat in scene.beats:
                    if beat.type == "dialogue" and beat.character:
                        # 用角色 ID 替换名称（如果存在映射）
                        char_id = char_id_map.get(beat.character)
                        if char_id:
                            beat.character = char_id

        # ── 构建章节 ──
        chapters = []
        for number, title, scenes in chapter_scripts:
            chapters.append(
                ChapterScript(number=number, title=title, scenes=scenes)
            )

        total_scenes = sum(len(ch.scenes) for ch in chapters)
        total_beats = sum(len(s.beats) for ch in chapters for s in ch.scenes)
        total_shots = sum(len(s.shots) for ch in chapters for s in ch.scenes)

        # ── 生成 logline ──
        logline = ""
        if chapter_report and chapter_report.analyses:
            logline = self._generate_logline(novel_name, chapter_report)

        # ── 组装 Script ──
        script = Script(
            title=f"{novel_name}",
            genre=genre,
            logline=logline,
            source={
                "type": "novel",
                "chapters": [ch.number for ch in chapters],
            },
            characters=script_characters,
            metadata=ScriptMetadata(
                source_novel=novel_name,
                total_chapters=len(chapters),
                total_scenes=total_scenes,
                total_beats=total_beats,
                total_shots=total_shots,
                generated_at=datetime.now(timezone.utc).isoformat(),
            ),
            chapters=chapters,
        )

        self.logger.info(
            f"脚本组装完成: {len(chapters)} 章, {total_scenes} 场景, "
            f"{total_beats} 节拍, {total_shots} 镜头, "
            f"{len(script_characters)} 角色"
        )
        return script

    def _generate_logline(
        self, novel_name: str, chapter_report: ChapterAnalysisReport
    ) -> str:
        """从章节摘要中提取或生成一句话梗概。

        Args:
            novel_name: 小说名。
            chapter_report: 章节分析报告。

        Returns:
            一句话梗概。
        """
        # 拼接前两章摘要作为 LLM 输入
        summaries = [a.summary for a in chapter_report.analyses[:3]]
        combined = " ".join(summaries)
        if not combined.strip():
            return ""

        try:
            result = self.llm_prompt(
                "script_assembly",
                f"请基于以下小说摘要，用一句话（不超过50字）概括整个故事的核心冲突与主线：\n\n{combined}",
            )
            # 清理结果
            logline = result.strip().strip('"').strip("'")
            if len(logline) > 100:
                logline = logline[:100]
            return logline
        except Exception:
            # LLM 失败不阻断组装
            return ""

    def build_char_id_map(
        self, characters: CharacterList
    ) -> dict[str, str]:
        """构建角色名 → 角色 ID 的映射表。

        Args:
            characters: 角色列表。

        Returns:
            {角色名: 角色ID} 的字典。
        """
        char_id_map: dict[str, str] = {}
        sorted_chars = sorted(
            characters.characters,
            key=lambda c: c.importance,
            reverse=True,
        )
        for i, char in enumerate(sorted_chars):
            char_id = f"char_{i + 1:03d}"
            char_id_map[char.name] = char_id
            for alias in char.aliases:
                char_id_map[alias] = char_id
        return char_id_map
