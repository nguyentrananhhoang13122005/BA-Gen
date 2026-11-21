"""Quản lý lưu trữ SQLite và bộ nhớ đệm SHA-256 cho hệ thống BA-Gen.

Tạo và quản lý các bảng:
- projects
- requirements
- user_stories
- llm_cache (giúp tối ưu chi phí và tránh gọi API trùng lặp)
"""

import hashlib
import json
import sqlite3
from typing import List, Optional
from src.core.config import get_config
from src.core.models import ProjectDTO, RequirementDTO, UserStoryDTO


class DatabaseManager:
    """Quản lý kết nối và các thao tác CRUD với SQLite database."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_config().database_path
        self._memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Khởi tạo toàn bộ cấu trúc bảng nếu chưa tồn tại."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Bảng projects
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    source_filename TEXT,
                    language TEXT DEFAULT 'vi',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Bảng requirements
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS requirements (
                    req_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    raw_text TEXT NOT NULL,
                    req_type TEXT DEFAULT 'FR',
                    nfr_category TEXT,
                    confidence REAL DEFAULT 1.0,
                    is_ambiguous INTEGER DEFAULT 0,
                    vague_terms_json TEXT,
                    missing_actor INTEGER DEFAULT 0,
                    missing_metric INTEGER DEFAULT 0,
                    smart_rewrite TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects (project_id)
                )
            """)

            # Bảng user_stories
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_stories (
                    story_id TEXT PRIMARY KEY,
                    req_id TEXT,
                    role TEXT,
                    goal TEXT,
                    benefit TEXT,
                    acceptance_criteria_json TEXT,
                    puml_usecase_name TEXT,
                    FOREIGN KEY (req_id) REFERENCES requirements (req_id)
                )
            """)

            # Bảng llm_cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_cache (
                    cache_key TEXT PRIMARY KEY,
                    req_hash TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            if self._memory_conn is None:
                conn.close()

    @staticmethod
    def generate_cache_key(text: str, provider: str, model_name: str) -> str:
        """Tạo khóa băm SHA-256 từ nội dung câu, provider và model."""
        raw_key = f"{text.strip()}::{provider.strip()}::{model_name.strip()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get_cache(self, cache_key: str) -> Optional[dict]:
        """Truy xuất kết quả đệm LLM từ khóa SHA-256."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT response_json FROM llm_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row["response_json"])
                except Exception:
                    return None
            return None
        finally:
            if self._memory_conn is None:
                conn.close()

    def set_cache(self, text: str, provider: str, model_name: str, response_data: dict):
        """Lưu kết quả phản hồi của LLM vào bộ nhớ đệm."""
        cache_key = self.generate_cache_key(text, provider, model_name)
        req_hash = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        response_json = json.dumps(response_data, ensure_ascii=False)
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO llm_cache (cache_key, req_hash, provider, model_name, response_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cache_key, req_hash, provider, model_name, response_json),
            )
            conn.commit()
        finally:
            if self._memory_conn is None:
                conn.close()

    def save_project(self, project: ProjectDTO):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO projects (project_id, project_name, source_filename, language)
                VALUES (?, ?, ?, ?)
                """,
                (project.project_id, project.project_name, project.source_filename, project.language),
            )
            conn.commit()
        finally:
            if self._memory_conn is None:
                conn.close()

    def save_requirements(self, requirements: List[RequirementDTO]):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            for req in requirements:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO requirements (
                        req_id, project_id, raw_text, req_type, nfr_category,
                        confidence, is_ambiguous, vague_terms_json,
                        missing_actor, missing_metric, smart_rewrite
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        req.req_id,
                        req.project_id,
                        req.raw_text,
                        req.req_type,
                        req.nfr_category,
                        req.confidence,
                        1 if req.is_ambiguous else 0,
                        json.dumps(req.vague_terms, ensure_ascii=False),
                        1 if req.missing_actor else 0,
                        1 if req.missing_metric else 0,
                        req.smart_rewrite,
                    ),
                )
            conn.commit()
        finally:
            if self._memory_conn is None:
                conn.close()

    def save_user_stories(self, stories: List[UserStoryDTO]):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            for us in stories:
                ac_list = [ac.model_dump() for ac in us.acceptance_criteria]
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO user_stories (
                        story_id, req_id, role, goal, benefit,
                        acceptance_criteria_json, puml_usecase_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        us.story_id,
                        us.req_id,
                        us.role,
                        us.goal,
                        us.benefit,
                        json.dumps(ac_list, ensure_ascii=False),
                        us.puml_usecase_name,
                    ),
                )
            conn.commit()
        finally:
            if self._memory_conn is None:
                conn.close()
