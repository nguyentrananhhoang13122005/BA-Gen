"""Quản lý lưu trữ SQLite và bộ nhớ đệm SHA-256 cho hệ thống BA-Gen.

Tạo và quản lý các bảng:
- projects
- requirements (khóa chính phức hợp theo dự án)
- user_stories (khóa chính phức hợp theo dự án)
- llm_cache (giúp tối ưu chi phí và tránh gọi API trùng lặp)

CSDL dùng WAL + busy_timeout để nhiều phiên đọc/ghi song song an toàn, và tự
động migrate từ schema cũ (req_id/story_id là khóa chính toàn cục).
"""

import hashlib
import json
import sqlite3
from typing import List, Optional
from src.core.config import get_config
from src.core.models import ProjectDTO, RequirementDTO, UserStoryDTO


CREATE_PROJECTS_SQL = """
    CREATE TABLE IF NOT EXISTS projects (
        project_id TEXT PRIMARY KEY,
        owner_id TEXT,
        project_name TEXT NOT NULL,
        source_filename TEXT,
        language TEXT DEFAULT 'vi',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""

CREATE_REQUIREMENTS_SQL = """
    CREATE TABLE IF NOT EXISTS requirements (
        project_id TEXT NOT NULL,
        req_id TEXT NOT NULL,
        raw_text TEXT NOT NULL,
        req_type TEXT DEFAULT 'FR',
        nfr_category TEXT,
        confidence REAL DEFAULT 1.0,
        is_ambiguous INTEGER DEFAULT 0,
        vague_terms_json TEXT,
        missing_actor INTEGER DEFAULT 0,
        missing_metric INTEGER DEFAULT 0,
        smart_rewrite TEXT,
        PRIMARY KEY (project_id, req_id),
        FOREIGN KEY (project_id) REFERENCES projects (project_id)
    )
"""

CREATE_USER_STORIES_SQL = """
    CREATE TABLE IF NOT EXISTS user_stories (
        project_id TEXT NOT NULL,
        story_id TEXT NOT NULL,
        req_id TEXT,
        role TEXT,
        goal TEXT,
        benefit TEXT,
        acceptance_criteria_json TEXT,
        puml_usecase_name TEXT,
        PRIMARY KEY (project_id, story_id),
        FOREIGN KEY (project_id) REFERENCES projects (project_id)
    )
"""

CREATE_LLM_CACHE_SQL = """
    CREATE TABLE IF NOT EXISTS llm_cache (
        cache_key TEXT PRIMARY KEY,
        req_hash TEXT NOT NULL,
        provider TEXT NOT NULL,
        model_name TEXT NOT NULL,
        response_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
"""


class DatabaseManager:
    """Quản lý kết nối và các thao tác CRUD với SQLite database."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_config().database_path
        self._memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._memory_conn = self._configure_connection(
                sqlite3.connect(":memory:", check_same_thread=False)
            )
        self.init_db()

    def _configure_connection(self, conn: sqlite3.Connection) -> sqlite3.Connection:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def get_connection(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        return self._configure_connection(sqlite3.connect(self.db_path, timeout=10))

    def init_db(self):
        """Khởi tạo toàn bộ cấu trúc bảng nếu chưa tồn tại."""
        conn = self.get_connection()
        try:
            self._migrate_legacy_schema(conn)
            cursor = conn.cursor()
            cursor.execute(CREATE_PROJECTS_SQL)
            cursor.execute(CREATE_REQUIREMENTS_SQL)
            cursor.execute(CREATE_USER_STORIES_SQL)
            cursor.execute(CREATE_LLM_CACHE_SQL)
            conn.commit()
        finally:
            if self._memory_conn is None:
                conn.close()

    def _migrate_legacy_schema(self, conn: sqlite3.Connection):
        """Migrate schema cũ sang khóa chính phức hợp, giữ lại dữ liệu đọc được."""
        cursor = conn.cursor()
        tables = {
            row["name"]
            for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "requirements" not in tables:
            return

        project_columns = {
            row["name"] for row in cursor.execute("PRAGMA table_info(projects)")
        } if "projects" in tables else set()
        if project_columns and "owner_id" not in project_columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN owner_id TEXT")

        requirement_columns = list(cursor.execute("PRAGMA table_info(requirements)"))
        primary_key_columns = {row["name"] for row in requirement_columns if row["pk"] > 0}

        if primary_key_columns == {"project_id", "req_id"}:
            conn.commit()
            return

        has_user_stories = "user_stories" in tables
        conn.commit()
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            migration_sql = """
                BEGIN;

                ALTER TABLE requirements RENAME TO requirements_legacy;
                CREATE TABLE requirements (
                    project_id TEXT NOT NULL,
                    req_id TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    req_type TEXT DEFAULT 'FR',
                    nfr_category TEXT,
                    confidence REAL DEFAULT 1.0,
                    is_ambiguous INTEGER DEFAULT 0,
                    vague_terms_json TEXT,
                    missing_actor INTEGER DEFAULT 0,
                    missing_metric INTEGER DEFAULT 0,
                    smart_rewrite TEXT,
                    PRIMARY KEY (project_id, req_id),
                    FOREIGN KEY (project_id) REFERENCES projects (project_id)
                );
                INSERT OR REPLACE INTO requirements (
                    project_id, req_id, raw_text, req_type, nfr_category,
                    confidence, is_ambiguous, vague_terms_json,
                    missing_actor, missing_metric, smart_rewrite
                )
                SELECT
                    COALESCE(NULLIF(project_id, ''), 'legacy_project'), req_id, raw_text,
                    req_type, nfr_category, confidence, is_ambiguous, vague_terms_json,
                    missing_actor, missing_metric, smart_rewrite
                FROM requirements_legacy;
                DROP TABLE requirements_legacy;
            """

            if has_user_stories:
                migration_sql += """
                    ALTER TABLE user_stories RENAME TO user_stories_legacy;
                    CREATE TABLE user_stories (
                        project_id TEXT NOT NULL,
                        story_id TEXT NOT NULL,
                        req_id TEXT,
                        role TEXT,
                        goal TEXT,
                        benefit TEXT,
                        acceptance_criteria_json TEXT,
                        puml_usecase_name TEXT,
                        PRIMARY KEY (project_id, story_id),
                        FOREIGN KEY (project_id) REFERENCES projects (project_id)
                    );
                    INSERT OR REPLACE INTO user_stories (
                        project_id, story_id, req_id, role, goal, benefit,
                        acceptance_criteria_json, puml_usecase_name
                    )
                    SELECT
                        COALESCE(r.project_id, 'legacy_project'), s.story_id, s.req_id,
                        s.role, s.goal, s.benefit, s.acceptance_criteria_json, s.puml_usecase_name
                    FROM user_stories_legacy s
                    LEFT JOIN requirements r ON r.req_id = s.req_id;
                    DROP TABLE user_stories_legacy;
                """

            migration_sql += """
                INSERT OR IGNORE INTO projects (project_id, project_name, source_filename, language)
                SELECT 'legacy_project', 'Dự án cũ', NULL, 'vi'
                WHERE EXISTS (SELECT 1 FROM requirements WHERE project_id = 'legacy_project');

                COMMIT;
            """
            conn.executescript(migration_sql)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.execute("PRAGMA foreign_keys=ON")

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
                INSERT OR REPLACE INTO projects (
                    project_id, owner_id, project_name, source_filename, language, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    project.project_id,
                    project.owner_id,
                    project.project_name,
                    project.source_filename,
                    project.language,
                    project.created_at.isoformat(),
                ),
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
                        project_id, req_id, raw_text, req_type, nfr_category,
                        confidence, is_ambiguous, vague_terms_json,
                        missing_actor, missing_metric, smart_rewrite
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        req.project_id,
                        req.req_id,
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
                        project_id, story_id, req_id, role, goal, benefit,
                        acceptance_criteria_json, puml_usecase_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        us.project_id,
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
