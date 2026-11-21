"""Máy chủ API Backend (FastAPI) & Phục vụ Giao diện React SPA cho BA-Gen.

Thay thế hoàn toàn Streamlit bằng kiến trúc REST API + React Frontend,
hoạt động 100% trên dữ liệu thật của người dùng và kết nối AI thực tế.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

from src.classifiers.llm_client import (  # noqa: E402
    MultiLLMClient,
    is_ollama_running,
    is_real_api_key,
)
from src.core.config import get_config  # noqa: E402
from src.core.facade import RequirementAnalysisFacade  # noqa: E402
from src.core.sessions import SESSION_COOKIE_NAME, SessionManager, SessionState  # noqa: E402
from src.core.static_files import is_unsafe_relative_path, resolve_file_under  # noqa: E402

app = FastAPI(
    title="BA-Gen API — Requirements Engineering Assistant",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


session_manager = SessionManager()


@app.middleware("http")
async def attach_session(request: Request, call_next):
    """Gắn phiên riêng cho mỗi client và phát cookie đã ký khi tạo phiên mới."""
    session, new_token = session_manager.get_or_create(request.cookies.get(SESSION_COOKIE_NAME))
    request.state.session = session
    response = await call_next(request)
    if new_token:
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=new_token,
            max_age=session_manager.ttl_seconds,
            httponly=True,
            samesite="lax",
            secure=session_manager.secure_cookie,
            path="/",
        )
    return response


def get_session(request: Request) -> SessionState:
    """FastAPI dependency: trả về phiên đã được middleware gắn vào request."""
    return request.state.session


class SmartRewriteRequest(BaseModel):
    new_text: Optional[str] = None


class UpdateTypeRequest(BaseModel):
    req_type: str
    nfr_category: Optional[str] = None


class JiraSyncRequest(BaseModel):
    domain: str
    email: str
    token: str
    project_key: str = "PROJ"


class GitHubSyncRequest(BaseModel):
    repo: str
    token: str


class TrelloSyncRequest(BaseModel):
    api_key: str
    token: str
    list_id: str


def _serialize_current_result(facade: RequirementAnalysisFacade) -> dict:
    """Chuyển đổi trạng thái phân tích hiện tại sang JSON trả về cho React Frontend."""
    if not facade.current_project:
        raise HTTPException(status_code=404, detail="Chưa có phiên phân tích nào được khởi tạo.")

    res = facade.get_current_result()
    return {
        "project": {
            "project_id": res.project.project_id,
            "project_name": res.project.project_name,
            "source_filename": res.project.source_filename,
            "language": res.project.language,
            "created_at": res.project.created_at.isoformat(),
        },
        "requirements": [r.model_dump() for r in res.requirements],
        "user_stories": [u.model_dump() for u in res.user_stories],
        "plantuml_code": res.plantuml_code,
        "has_diagram_image": bool(res.plantuml_image_bytes),
        "timings": res.timings,
        "warnings": res.warnings,
        "srs_markdown": facade.export_srs_markdown(),
    }


async def _read_upload_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Đọc tệp theo từng khối 1 MB và dừng ngay khi vượt giới hạn."""
    chunks = []
    total = 0
    limit_mb = max_bytes // (1024 * 1024)
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Tệp vượt quá giới hạn {limit_mb} MB. Vui lòng chia nhỏ tài liệu.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@app.get("/api/config-defaults")
def get_config_defaults():
    """Trả về cấu hình mặc định từ môi trường và trạng thái Ollama (không lộ khóa)."""
    config = get_config()
    groq_env = os.getenv("GROQ_API_KEY", "")
    gemini_env = os.getenv("GEMINI_API_KEY", "")
    openrouter_env = os.getenv("OPENROUTER_API_KEY", "")
    return {
        "default_provider": config.default_provider,
        "default_model": config.model_for(config.default_provider),
        "confidence_threshold": config.confidence_threshold,
        "models": dict(config.models),
        "has_env_groq": is_real_api_key(groq_env),
        "has_env_gemini": is_real_api_key(gemini_env),
        "has_env_openrouter": is_real_api_key(openrouter_env),
        "ollama_running": is_ollama_running(),
    }


@app.post("/api/analyze")
async def analyze_requirements(
    provider: Optional[str] = Form(None),
    api_key: str = Form(""),
    model_name: str = Form(""),
    confidence_threshold: Optional[float] = Form(None),
    project_name: str = Form(""),
    raw_text: str = Form(""),
    file: Optional[UploadFile] = File(None),
    session: SessionState = Depends(get_session),
):
    """Phân tích tài liệu yêu cầu thực tế qua đường ống AI/NLP 6 bước."""
    config = get_config()
    clean_provider = (provider or config.default_provider).lower().strip()
    if confidence_threshold is None:
        confidence_threshold = config.confidence_threshold
    elif not 0.0 <= confidence_threshold <= 1.0:
        raise HTTPException(
            status_code=400,
            detail="Ngưỡng tin cậy (confidence_threshold) phải nằm trong khoảng 0..1.",
        )
    effective_key = api_key.strip()

    if not effective_key and clean_provider in ("groq", "gemini", "openrouter"):
        env_map = {
            "groq": "GROQ_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        env_candidate = os.getenv(env_map[clean_provider], "")
        if is_real_api_key(env_candidate):
            effective_key = env_candidate

    if clean_provider in ("groq", "gemini", "openrouter") and not is_real_api_key(effective_key):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Bạn đang chọn cổng {clean_provider.upper()} nhưng chưa nhập API Key. "
                "Vui lòng dán API Key hoặc chọn 'Mô hình NLP & Học máy Tích hợp trên máy' để chạy trực tiếp."
            ),
        )

    if file is not None and file.filename:
        content_bytes = await _read_upload_limited(file, config.max_file_size_bytes)
        source = content_bytes
        filename = file.filename
        size_bytes = len(content_bytes)
    elif raw_text.strip():
        stripped_text = raw_text.strip()
        if len(stripped_text) > config.max_raw_text_chars:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Văn bản dán vào có {len(stripped_text):,} ký tự, vượt giới hạn "
                    f"{config.max_raw_text_chars:,} ký tự."
                ),
            )
        source = stripped_text
        filename = "van_ban_yeu_cau.txt"
        size_bytes = len(source.encode("utf-8"))
    else:
        raise HTTPException(
            status_code=400,
            detail="Vui lòng tải lên tệp tài liệu (.docx / .txt) hoặc dán nội dung yêu cầu cần phân tích.",
        )

    # Nếu chọn local_nlp hoặc chọn ollama nhưng máy chưa cài/bật Ollama port 11434 -> chạy bộ NLP + ML tích hợp
    use_cloud_llm = clean_provider in ("groq", "gemini", "openrouter")
    use_ollama_live = (clean_provider == "ollama") and is_ollama_running()
    active_llm_mode = use_cloud_llm or use_ollama_live

    llm_client = MultiLLMClient(
        provider=clean_provider if active_llm_mode else "local_nlp",
        api_key=effective_key,
        model_name=model_name.strip() or None,
    )

    with session.lock:
        session.facade = RequirementAnalysisFacade(
            llm_client=llm_client,
            confidence_threshold=confidence_threshold,
            force_llm_mode=active_llm_mode,
            strict_llm=use_cloud_llm,
            owner_id=session.owner_id,
        )

        try:
            session.facade.analyze_document(
                source=source,
                filename=filename,
                file_size_bytes=size_bytes,
                project_name=project_name.strip() or None,
            )
            return _serialize_current_result(session.facade)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve)) from ve
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/requirements/{req_id}/apply-smart")
def apply_smart_single(
    req_id: str,
    body: SmartRewriteRequest,
    session: SessionState = Depends(get_session),
):
    """Áp dụng câu viết lại chuẩn SMART cho một yêu cầu cụ thể."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=400, detail="Chưa có dữ liệu phân tích.")
        session.facade.apply_smart_rewrite(req_id, new_text=body.new_text)
        return _serialize_current_result(session.facade)


@app.post("/api/requirements/apply-smart-all")
def apply_smart_all(session: SessionState = Depends(get_session)):
    """Áp dụng câu viết lại chuẩn SMART cho toàn bộ các câu đang bị mơ hồ."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=400, detail="Chưa có dữ liệu phân tích.")
        for req in session.facade.current_requirements:
            if req.is_ambiguous and req.smart_rewrite:
                req.raw_text = req.smart_rewrite
                req.is_ambiguous = False
                req.vague_terms = []
                req.missing_actor = False
                req.missing_metric = False
        session.facade.db.save_requirements(session.facade.current_requirements)
        session.facade.resync_artifacts()
        return _serialize_current_result(session.facade)


@app.post("/api/requirements/{req_id}/update-type")
def update_requirement_type(
    req_id: str,
    body: UpdateTypeRequest,
    session: SessionState = Depends(get_session),
):
    """Cập nhật nhãn phân loại FR/NFR và danh mục ISO 25010 cho một câu yêu cầu."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=400, detail="Chưa có dữ liệu phân tích.")
        session.facade.update_requirement_type(req_id, body.req_type, body.nfr_category)
        return _serialize_current_result(session.facade)


@app.get("/api/export/srs-docx")
def export_srs_docx(session: SessionState = Depends(get_session)):
    """Tải tệp báo cáo đặc tả SRS định dạng Microsoft Word (.docx)."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=404, detail="Chưa có dữ liệu phân tích.")
        docx_bytes = session.facade.export_srs_docx()
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="SRS_Specification.docx"'},
        )


@app.get("/api/export/srs-md")
def export_srs_md(session: SessionState = Depends(get_session)):
    """Tải tệp báo cáo đặc tả SRS định dạng Markdown (.md)."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=404, detail="Chưa có dữ liệu phân tích.")
        md_text = session.facade.export_srs_markdown()
        return Response(
            content=md_text.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="SRS_Specification.md"'},
        )


@app.get("/api/export/diagram-png")
def export_diagram_png(session: SessionState = Depends(get_session)):
    """Trả về ảnh PNG sơ đồ Use Case UML 2.5."""
    with session.lock:
        if not session.facade.current_plantuml_bytes:
            raise HTTPException(status_code=404, detail="Chưa có ảnh sơ đồ Use Case.")
        return Response(
            content=session.facade.current_plantuml_bytes,
            media_type="image/png",
            headers={"Content-Disposition": 'inline; filename="usecase_diagram.png"'},
        )


@app.get("/api/export/diagram-puml")
def export_diagram_puml(session: SessionState = Depends(get_session)):
    """Tải mã nguồn PlantUML (.puml)."""
    with session.lock:
        if not session.facade.current_plantuml_code:
            raise HTTPException(status_code=404, detail="Chưa có mã PlantUML.")
        return Response(
            content=session.facade.current_plantuml_code.encode("utf-8"),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="usecase_diagram.puml"'},
        )


@app.get("/api/export/jira-csv")
def export_jira_csv(session: SessionState = Depends(get_session)):
    """Tải tệp CSV chuẩn Jira Issue Import."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=404, detail="Chưa có dữ liệu phân tích.")
        csv_data = session.facade.export_jira_csv()
        return Response(
            content=csv_data.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="jira_stories_import.csv"'},
        )


@app.get("/api/export/github-json")
def export_github_json(session: SessionState = Depends(get_session)):
    """Tải tệp JSON chuẩn GitHub Issues."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=404, detail="Chưa có dữ liệu phân tích.")
        json_data = session.facade.export_github_json()
        return Response(
            content=json_data.encode("utf-8"),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="github_issues_export.json"'},
        )


@app.get("/api/export/trello-json")
def export_trello_json(session: SessionState = Depends(get_session)):
    """Tải tệp JSON chuẩn Trello Board."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=404, detail="Chưa có dữ liệu phân tích.")
        json_data = session.facade.export_trello_json()
        return Response(
            content=json_data.encode("utf-8"),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="trello_board_export.json"'},
        )


@app.post("/api/sync/jira")
def sync_jira(req: JiraSyncRequest, session: SessionState = Depends(get_session)):
    """Đồng bộ User Stories trực tiếp lên Jira Cloud REST API v3."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=400, detail="Chưa có dữ liệu phân tích.")
        return session.facade.sync_to_jira(req.domain, req.email, req.token, req.project_key)


@app.post("/api/sync/github")
def sync_github(req: GitHubSyncRequest, session: SessionState = Depends(get_session)):
    """Đồng bộ User Stories trực tiếp lên GitHub Issues REST API."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=400, detail="Chưa có dữ liệu phân tích.")
        return session.facade.sync_to_github(req.repo, req.token)


@app.post("/api/sync/trello")
def sync_trello(req: TrelloSyncRequest, session: SessionState = Depends(get_session)):
    """Đồng bộ User Stories trực tiếp lên Trello Board REST API."""
    with session.lock:
        if not session.facade.current_project:
            raise HTTPException(status_code=400, detail="Chưa có dữ liệu phân tích.")
        return session.facade.sync_to_trello(req.api_key, req.token, req.list_id)


# Phục vụ giao diện React SPA đã build tại thư mục frontend/dist
FRONTEND_DIST = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
)
if os.path.exists(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")


@app.get("/{full_path:path}")
def serve_react_spa(full_path: str):
    """Phục vụ tệp tĩnh hoặc index.html của React SPA."""
    if is_unsafe_relative_path(full_path):
        raise HTTPException(status_code=404, detail="Tệp không tồn tại.")
    served_file = resolve_file_under(FRONTEND_DIST, full_path)
    if served_file:
        return FileResponse(served_file)
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "BA-Gen API Server is running. Build frontend into frontend/dist to view UI."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8501, reload=False)
