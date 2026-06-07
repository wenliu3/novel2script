"""主流水线：切分章节 → 并行 LLM 转换 → 按顺序合并 → 导出 YAML。

每个章节独立处理，无滑动窗口，多章节并行加速。
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from app.core.agent import ScriptAgent, _try_parse_yaml
from app.core.builder import export_yaml
from app.core.splitter import smart_split, read_file, clean_text, TextChunk
from app.llm import LLM
from app.models import Screenplay, fix_llm_data

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None]


def _convert_one_chunk(agent: ScriptAgent, chunk: TextChunk) -> tuple[int, int, str]:
    """转换单个章节，返回 (排序索引, 章节编号, YAML 字符串)。"""
    ch_num = chunk.chapter_number or (chunk.index + 1)
    logger.info(f"转换第 {ch_num} 章（{len(chunk.text):,} 字）: {chunk.title}")
    yaml_str = agent.convert_chunk(chunk.text, chapter_title=chunk.title, chapter_number=ch_num)
    return chunk.index, ch_num, yaml_str


def _merge_results(results: list[tuple[int, int, str]], novel_name: str = "") -> Screenplay:
    """按章节索引排序后合并所有 YAML 结果。"""
    results.sort(key=lambda r: r[0])

    characters: dict[str, str] = {}
    title = novel_name or "未命名剧本"
    author = None
    genre = None

    all_chapter_dicts: list[dict] = []

    for sort_idx, ch_num, yaml_str in results:
        data = _try_parse_yaml(yaml_str)
        if not data:
            logger.warning(f"跳过第 {ch_num} 章（YAML 解析失败）")
            continue

        data = fix_llm_data(data)

        # 从第一个有效块取 author/genre
        if author is None and data.get("author"):
            author = data["author"]
        if genre is None and data.get("genre"):
            genre = data["genre"]

        # 合并角色表
        chunk_chars = data.get("characters", {})
        if isinstance(chunk_chars, dict):
            characters.update(chunk_chars)

        for ch in data.get("chapters", []):
            ch["chapter_number"] = ch_num  # 保留原始章节编号
            all_chapter_dicts.append(ch)

    if not all_chapter_dicts:
        raise ValueError("LLM 未生成任何章节")

    screenplay = Screenplay(
        title=title,
        author=author,
        genre=genre,
        characters=characters,
        chapters=all_chapter_dicts,
    )

    logger.info(f"合并完成: {len(all_chapter_dicts)} 章, {len(characters)} 角色")
    return screenplay


def run_pipeline(
    input_path: str,
    output_path: str,
    llm: LLM,
    novel_name: str = "",
    chunk_size: int = 100_000,
    max_workers: int = 5,
    on_progress: ProgressCallback | None = None,
) -> str:
    """执行小说转剧本流水线。

    Args:
        input_path: 输入小说文件路径。
        output_path: 输出 YAML 文件路径。
        llm: LLM 服务实例。
        novel_name: 小说名称（用作 YAML title）。
        chunk_size: 每块最大字符数。
        max_workers: 并行处理的线程数。
        on_progress: 进度回调函数。

    Returns:
        输出 YAML 文件路径。
    """
    # ── 读取小说 ──
    _, text = read_file(Path(input_path))
    text = clean_text(text)
    logger.info(f"读取小说: {input_path} ({len(text):,} 字)")

    # ── 切分 ──
    chunks = smart_split(text, chunk_size)
    logger.info(f"切分为 {len(chunks)} 块，{max_workers} 线程并行处理")

    agent = ScriptAgent(llm)
    results: list[tuple[int, int, str]] = []
    completed = 0
    total = len(chunks)

    # ── 并行转换 ──
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_convert_one_chunk, agent, chunk): chunk
            for chunk in chunks
        }

        for future in as_completed(futures):
            chunk = futures[future]
            try:
                idx, ch_num, yaml_str = future.result()
                results.append((idx, ch_num, yaml_str))
                completed += 1
                if on_progress:
                    try:
                        on_progress(completed, total, f"已完成 {completed}/{total} 章: {chunk.title}")
                    except Exception:
                        pass
                logger.info(f"完成第 {idx + 1}/{total} 块: {chunk.title}")
            except Exception as e:
                completed += 1
                logger.error(f"第 {chunk.index + 1} 块失败: {chunk.title} - {e}")

    if not results:
        raise RuntimeError("所有章节转换均失败")

    # ── 合并 + 导出 ──
    if on_progress:
        try:
            on_progress(total, total, "正在合并并导出 YAML...")
        except Exception:
            pass

    screenplay = _merge_results(results, novel_name=novel_name)

    output = Path(output_path)
    export_yaml(screenplay, output.parent, output.name)

    logger.info(f"转换完成: {screenplay.total_scenes} 场景, {screenplay.total_characters} 角色")
    logger.info(f"输出: {output_path}")

    return output_path


def run_pipeline_with_status(
    input_path: str,
    output_path: str,
    llm: LLM,
    novel_name: str = "",
    chunk_size: int = 100_000,
    max_workers: int = 5,
    status_store: dict | None = None,
    task_id: str = "",
) -> str:
    """带状态更新的流水线（供 API 使用）。"""
    def on_progress(current: int, total: int, msg: str):
        if status_store is not None and task_id:
            status_store[task_id]["progress"] = f"{current}/{total}"
            status_store[task_id]["message"] = msg

    return run_pipeline(input_path, output_path, llm, novel_name, chunk_size, max_workers, on_progress)
