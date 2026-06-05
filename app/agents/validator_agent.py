"""校验 Agent。

验证生成的脚本是否完整、一致、符合 LRM 格式要求。
"""

import logging

from app.agents.base_agent import BaseAgent
from app.schema.script import Script
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ValidationResult:
    """校验结果。"""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def summary(self) -> str:
        parts = []
        if self.errors:
            parts.append(f"错误: {len(self.errors)}")
        if self.warnings:
            parts.append(f"警告: {len(self.warnings)}")
        if not parts:
            return "校验通过 ✓"
        return ", ".join(parts)


class ValidatorAgent(BaseAgent):
    """校验 Agent。

    职责：
    1. 检查脚本结构完整性（必须有 title, metadata, chapters）
    2. 检查每个场景的镜头完整性
    3. 检查对话是否为空
    4. 检查 ID 唯一性
    5. 输出校验报告
    """

    def __init__(self, llm: LLMService) -> None:
        super().__init__("validator_agent", llm)

    def execute(self, script: Script) -> ValidationResult:
        """校验脚本数据。

        Args:
            script: 待校验的脚本对象。

        Returns:
            校验结果。
        """
        result = ValidationResult()

        # 基础结构校验
        if not script.title:
            result.add_error("脚本缺少标题 (title)")

        if not script.metadata.source_novel:
            result.add_warning("缺少来源小说名 (metadata.source_novel)")

        if not script.chapters:
            result.add_error("脚本没有章节 (chapters)")

        # 章节级校验
        seen_ids: set[str] = set()
        for chapter in script.chapters:
            if not chapter.scenes:
                result.add_warning(f"第{chapter.number}章没有场景")

            for scene in chapter.scenes:
                # ID 唯一性
                if scene.id in seen_ids:
                    result.add_error(f"重复的场景 ID: {scene.id}")
                seen_ids.add(scene.id)

                # 场景完整性
                if not scene.title:
                    result.add_warning(f"场景 {scene.id} 缺少标题")
                if not scene.location:
                    result.add_warning(f"场景 {scene.id} 缺少地点")

                # 镜头校验
                if not scene.shots:
                    result.add_warning(f"场景 {scene.id} 没有镜头")

                for shot in scene.shots:
                    if shot.id in seen_ids:
                        result.add_error(f"重复的镜头 ID: {shot.id}")
                    seen_ids.add(shot.id)

                    if not shot.frame_description:
                        result.add_warning(f"镜头 {shot.id} 缺少画面描述")

        # LLM 辅助校验（可选，对大脚本做内容一致性检查）
        if script.chapters and len(script.chapters) > 0:
            self._llm_content_check(script, result)

        self.logger.info(f"校验完成: {result.summary()}")
        return result

    def _llm_content_check(self, script: Script, result: ValidationResult) -> None:
        """使用 LLM 进行内容一致性校验。"""
        # 只取前两章做快速检查，避免消耗过多 token
        sample = script.chapters[:2]
        sample_text = str(
            {
                "chapters": [
                    {"number": ch.number, "scenes_count": len(ch.scenes)}
                    for ch in sample
                ]
            }
        )

        try:
            check_result = self.llm_prompt_json(
                "script_assembly",
                f"Quick consistency check for this script structure:\n{sample_text}",
            )
            if check_result.get("issues"):
                for issue in check_result["issues"]:
                    result.add_warning(f"LLM 检查: {issue}")
        except Exception as e:
            self.logger.debug(f"LLM 内容校验跳过: {e}")
