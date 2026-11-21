"""Kiểm thử schema SQLite: UUID, khóa chính phức hợp, WAL và migration."""

import sqlite3

from src.core.database import DatabaseManager
from src.core.facade import RequirementAnalysisFacade
from src.core.models import ProjectDTO, RequirementDTO, UserStoryDTO


def _primary_key_columns(db: DatabaseManager, table: str):
    conn = db.get_connection()
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {row["name"] for row in rows if row["pk"] > 0}
    finally:
        if db._memory_conn is None:
            conn.close()


def test_schema_uses_composite_primary_keys():
    db = DatabaseManager(":memory:")

    assert _primary_key_columns(db, "requirements") == {"project_id", "req_id"}
    assert _primary_key_columns(db, "user_stories") == {"project_id", "story_id"}


def test_two_projects_keep_same_req_and_story_ids_separate():
    db = DatabaseManager(":memory:")
    db.save_project(ProjectDTO(project_id="P1", project_name="Dự án 1", source_filename="a.txt"))
    db.save_project(ProjectDTO(project_id="P2", project_name="Dự án 2", source_filename="b.txt"))

    db.save_requirements([
        RequirementDTO(req_id="REQ-01", project_id="P1", raw_text="Câu của dự án 1"),
        RequirementDTO(req_id="REQ-01", project_id="P2", raw_text="Câu của dự án 2"),
    ])
    db.save_user_stories([
        UserStoryDTO(story_id="US-01", req_id="REQ-01", project_id="P1", role="A", goal="G1", benefit="B1"),
        UserStoryDTO(story_id="US-01", req_id="REQ-01", project_id="P2", role="B", goal="G2", benefit="B2"),
    ])

    conn = db.get_connection()
    try:
        req_rows = conn.execute(
            "SELECT project_id, raw_text FROM requirements ORDER BY project_id"
        ).fetchall()
        story_rows = conn.execute(
            "SELECT project_id, goal FROM user_stories ORDER BY project_id"
        ).fetchall()
    finally:
        conn.close()

    assert [(row["project_id"], row["raw_text"]) for row in req_rows] == [
        ("P1", "Câu của dự án 1"),
        ("P2", "Câu của dự án 2"),
    ]
    assert [(row["project_id"], row["goal"]) for row in story_rows] == [("P1", "G1"), ("P2", "G2")]


def test_project_ids_are_unique_uuid4_and_owner_is_persisted():
    db = DatabaseManager(":memory:")
    facade = RequirementAnalysisFacade(db_manager=db, owner_id="session-abc")

    first = facade.analyze_document(source="Người dùng có thể đăng nhập.", filename="a.txt")
    second = facade.analyze_document(source="Người dùng có thể đăng xuất.", filename="b.txt")

    assert first.project.project_id.startswith("PROJ-")
    assert first.project.project_id != second.project.project_id
    assert first.project.owner_id == "session-abc"

    conn = db.get_connection()
    try:
        owner = conn.execute(
            "SELECT owner_id FROM projects WHERE project_id = ?",
            (first.project.project_id,),
        ).fetchone()["owner_id"]
    finally:
        conn.close()
    assert owner == "session-abc"


def test_wal_busy_timeout_and_foreign_keys_enabled(tmp_path):
    db = DatabaseManager(str(tmp_path / "pragma.db"))
    conn = db.get_connection()
    try:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0].lower()
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        foreign_keys = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        conn.close()

    assert journal_mode == "wal"
    assert busy_timeout == 5000
    assert foreign_keys == 1


def _create_legacy_database(path: str):
    conn = sqlite3.connect(path)
    try:
        conn.executescript("""
            CREATE TABLE projects (
                project_id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                source_filename TEXT,
                language TEXT DEFAULT 'vi',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE requirements (
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
            );
            CREATE TABLE user_stories (
                story_id TEXT PRIMARY KEY,
                req_id TEXT,
                role TEXT,
                goal TEXT,
                benefit TEXT,
                acceptance_criteria_json TEXT,
                puml_usecase_name TEXT,
                FOREIGN KEY (req_id) REFERENCES requirements (req_id)
            );
            INSERT INTO projects (project_id, project_name)
                VALUES ('PROJ-legacy-1', 'Dự án Legacy');
            INSERT INTO requirements (req_id, project_id, raw_text)
                VALUES ('REQ-01', 'PROJ-legacy-1', 'Câu yêu cầu cũ.');
            INSERT INTO user_stories (
                story_id, req_id, role, goal, benefit, acceptance_criteria_json, puml_usecase_name
            ) VALUES ('US-01', 'REQ-01', 'Người dùng', 'mục tiêu cũ', 'giá trị cũ', '[]', '');
        """)
        conn.commit()
    finally:
        conn.close()


def test_legacy_database_is_migrated_without_losing_data(tmp_path):
    legacy_path = str(tmp_path / "legacy.db")
    _create_legacy_database(legacy_path)

    db = DatabaseManager(legacy_path)

    assert _primary_key_columns(db, "requirements") == {"project_id", "req_id"}
    assert _primary_key_columns(db, "user_stories") == {"project_id", "story_id"}

    conn = db.get_connection()
    try:
        project_columns = {row["name"] for row in conn.execute("PRAGMA table_info(projects)")}
        req_row = conn.execute(
            "SELECT project_id, raw_text FROM requirements WHERE req_id = 'REQ-01'"
        ).fetchone()
        story_row = conn.execute(
            "SELECT project_id, goal FROM user_stories WHERE story_id = 'US-01'"
        ).fetchone()
        leftover_tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_legacy'"
            )
        }
    finally:
        conn.close()

    assert "owner_id" in project_columns
    assert (req_row["project_id"], req_row["raw_text"]) == ("PROJ-legacy-1", "Câu yêu cầu cũ.")
    assert (story_row["project_id"], story_row["goal"]) == ("PROJ-legacy-1", "mục tiêu cũ")
    assert leftover_tables == set()

    db.save_project(ProjectDTO(project_id="P2", project_name="Dự án mới", source_filename="new.txt"))
    db.save_requirements([RequirementDTO(req_id="REQ-01", project_id="P2", raw_text="Câu mới")])

    conn = db.get_connection()
    try:
        req_count = conn.execute("SELECT COUNT(*) AS total FROM requirements").fetchone()["total"]
    finally:
        conn.close()
    assert req_count == 2

    DatabaseManager(legacy_path)
    conn = db.get_connection()
    try:
        req_count = conn.execute("SELECT COUNT(*) AS total FROM requirements").fetchone()["total"]
    finally:
        conn.close()
    assert req_count == 2
