"""脚本校验器。

提供独立于 Agent 的结构校验规则，可被 validator_agent 调用，
也可独立用于快速校验。
"""

from app.schema.script import Script


def validate_structure(script: Script) -> list[str]:
    """快速结构校验（不调用 LLM）。

    Args:
        script: 待校验的脚本。

    Returns:
        错误列表（空列表表示通过）。
    """
    errors = []

    if not script.title:
        errors.append("脚本缺少标题")

    if not script.chapters:
        errors.append("脚本没有章节")
        return errors

    seen_ids = set()
    for ch in script.chapters:
        for scene in ch.scenes:
            if scene.id in seen_ids:
                errors.append(f"重复 ID: {scene.id}")
            seen_ids.add(scene.id)

            for shot in scene.shots:
                if shot.id in seen_ids:
                    errors.append(f"重复 ID: {shot.id}")
                seen_ids.add(shot.id)

                if not shot.frame_description:
                    errors.append(f"镜头 {shot.id} 缺少画面描述")

    return errors
