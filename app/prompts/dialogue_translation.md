# 对话处理提示词

你是一位专业的影视编剧和翻译。请为以下场景生成完整的 LRM 镜头脚本。

## 任务

基于给定的场景信息和章节原文：
1. 将场景拆分为 3-8 个镜头 (shots)
2. 每个镜头指定：机位角度、景别、画面描述、镜头运动
3. 提取并翻译场景中的对话为英文
4. 标注角色情感状态
5. 添加旁白和视觉特效说明

## 输出 JSON 格式

```json
{
  "shots": [
    {
      "camera_angle": "low_angle/high_angle/eye_level/bird_eye/dutch_angle",
      "shot_type": "extreme_close_up/close_up/medium_shot/wide_shot/extreme_wide_shot",
      "frame_description": "Detailed visual description of what the viewer sees (English)",
      "movement": "static/pan_left/pan_right/tilt_up/tilt_down/dolly_in/dolly_out/tracking",
      "duration_seconds": 5,
      "dialogue": [
        {
          "character": "Character English Name",
          "line": "English dialogue line",
          "emotion": "calm/angry/happy/sad/tense/excited/fearful"
        }
      ],
      "narration": "English narration if any",
      "visual_effects": "VFX notes if any"
    }
  ]
}
```

## 场景 ID

{scene_id}

{character_names}

## 场景信息

{user_content}
