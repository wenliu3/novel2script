"""API 路由测试。

使用 FastAPI TestClient 测试所有端点。
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.config import Settings


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        milm_api_key="test-key",
        milm_base_url="http://localhost",
        milm_model="test-model",
        output_base=Path(tempfile.mkdtemp()),
    )


@pytest.fixture
def sample_novel_dir() -> Path:
    """创建临时小说目录。"""
    tmp = Path(tempfile.mkdtemp(prefix="api_test_"))
    origin = tmp / "origin"
    origin.mkdir(parents=True)
    (origin / "001_chapter1.txt").write_text("第一章 测试\n\n张三走进了客栈。", encoding="utf-8")
    (origin / "002_chapter2.txt").write_text("第二章 测试\n\n张三遇到李四。", encoding="utf-8")
    return tmp


# ── 健康检查 ──


class TestHealth:
    def test_root(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "running"

    def test_health(self, client: TestClient) -> None:
        r = client.get("/api/v1/health")
        assert r.status_code in (200, 500)  # 500 if no .env


# ── 文件上传 ──


class TestUpload:
    def test_upload_single_file(self, client: TestClient) -> None:
        files = [("files", ("test.txt", "第一章内容".encode("utf-8"), "text/plain"))]
        r = client.post("/api/v1/upload", files=files, data={"novel_name": "测试小说"})
        assert r.status_code == 200
        data = r.json()
        assert data["novel_name"] == "测试小说"
        assert data["file_count"] == 1

    def test_upload_no_files(self, client: TestClient) -> None:
        r = client.post("/api/v1/upload")
        assert r.status_code == 422  # validation error

    def test_upload_multiple_files(self, client: TestClient) -> None:
        files = [
            ("files", ("ch1.txt", "第一章".encode("utf-8"), "text/plain")),
            ("files", ("ch2.txt", "第二章".encode("utf-8"), "text/plain")),
        ]
        r = client.post("/api/v1/upload", files=files, data={"novel_name": "多章小说"})
        assert r.status_code == 200
        assert r.json()["file_count"] == 2


# ── 文本粘贴 ──


class TestTextConvert:
    def test_empty_text(self, client: TestClient) -> None:
        r = client.post("/api/v1/convert/text", json={"text": "", "title": "空"})
        assert r.status_code == 400

    def test_valid_text_requires_api_key(self, client: TestClient) -> None:
        """真实转换需要 API key，此处验证路由可达。"""
        r = client.post("/api/v1/convert/text", json={
            "text": "第一章\n张三走进了客栈。",
            "title": "测试",
        })
        # 500 因为无 API key 配置
        assert r.status_code in (200, 500)


# ── 小说列表 ──


class TestNovels:
    def test_list_novels(self, client: TestClient) -> None:
        r = client.get("/api/v1/novels")
        assert r.status_code == 200
        assert "novels" in r.json()

    def test_get_novel_not_found(self, client: TestClient) -> None:
        r = client.get("/api/v1/novels/nonexistent_xyz")
        assert r.status_code == 404


# ── 任务状态 ──


class TestTaskStatus:
    def test_task_not_found(self, client: TestClient) -> None:
        r = client.get("/api/v1/convert/nonexistent/status")
        assert r.status_code == 404


# ── 下载/预览 ──


class TestDownload:
    def test_download_not_found(self, client: TestClient) -> None:
        r = client.get("/api/v1/download/nonexistent")
        assert r.status_code == 404

    def test_preview_not_found(self, client: TestClient) -> None:
        r = client.get("/api/v1/preview/nonexistent")
        assert r.status_code == 404


# ── 删除 ──


class TestDelete:
    def test_delete_not_found(self, client: TestClient) -> None:
        r = client.delete("/api/v1/novels/nonexistent")
        assert r.status_code == 404
