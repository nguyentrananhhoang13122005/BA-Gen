"""Lớp điều phối trung tâm RequirementAnalysisFacade theo Facade Pattern.

Đóng vai trò là cổng giao tiếp duy nhất giữa giao diện người dùng Streamlit
và toàn bộ đường ống xử lý 6 bước phía sau. Hỗ trợ thao tác Human-in-the-Loop.
"""

import time
import uuid
from typing import Callable, List, Optional, Union
from src.analyzers.ambiguity_detector import AmbiguityDetector
from src.classifiers.hybrid_classifier import HybridClassifierStrategy
from src.classifiers.llm_client import MultiLLMClient
from src.core.config import get_config
from src.core.database import DatabaseManager
from src.core.models import AnalysisResultDTO, ProjectDTO, RequirementDTO, UserStoryDTO
from src.exporters.plantuml_exporter import PlantUMLExporter
from src.exporters.srs_builder import SRSBuilder
from src.generators.user_story_gen import UserStoryGenerator
from src.parsers.factory import DocumentIngestionFactory
from src.parsers.segmenter import RequirementSegmenter


class RequirementAnalysisFacade:
    """Facade điều phối toàn bộ chuỗi nghiệp vụ phân tích yêu cầu phần mềm."""

    def __init__(
        self,
        llm_client: Optional[MultiLLMClient] = None,
        db_manager: Optional[DatabaseManager] = None,
        confidence_threshold: Optional[float] = None,
        force_llm_mode: bool = False,
        strict_llm: bool = False,
        owner_id: Optional[str] = None,
    ):
        self.llm_client = llm_client or MultiLLMClient()
        self.db = db_manager or DatabaseManager()
        self.strict_llm = strict_llm
        self.owner_id = owner_id
        threshold = get_config().confidence_threshold if confidence_threshold is None else confidence_threshold
        self.classifier = HybridClassifierStrategy(
            llm_client=self.llm_client,
            db_manager=self.db,
            confidence_threshold=threshold,
            force_llm_mode=force_llm_mode,
            strict_llm=strict_llm,
        )
        self.ambiguity_detector = AmbiguityDetector(
            llm_client=self.llm_client,
            strict_llm=strict_llm,
        )
        self.user_story_gen = UserStoryGenerator(
            llm_client=self.llm_client,
            strict_llm=strict_llm,
        )
        self.plantuml_exporter = PlantUMLExporter()

        # Dữ liệu phiên hiện tại
        self.current_project: Optional[ProjectDTO] = None
        self.current_requirements: List[RequirementDTO] = []
        self.current_user_stories: List[UserStoryDTO] = []
        self.current_plantuml_code: str = ""
        self.current_plantuml_bytes: Optional[bytes] = None
        self.timings: dict = {}
        self.warnings: List[str] = []

    def analyze_document(
        self,
        source: Union[bytes, str],
        filename: str = "input.txt",
        file_size_bytes: int = 0,
        project_name: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str, str], None]] = None,
    ) -> AnalysisResultDTO:
        """Thực thi đường ống xử lý 6 bước từ tài liệu thô đến bộ đặc tả hoàn chỉnh."""
        total_start = time.perf_counter()
        timings = {}

        # Bước 1: Đọc tệp & tách câu nguyên tử
        if progress_callback:
            progress_callback(1, "INGEST & SEGMENT", "Đọc tài liệu nguồn & phân tách câu yêu cầu nguyên tử...")
        t0 = time.perf_counter()
        parser = DocumentIngestionFactory.create_parser(filename, file_size_bytes)
        raw_text = parser.parse(source)
        sentences, lang = RequirementSegmenter.segment(raw_text)
        timings["parsing_and_segmentation_sec"] = round(time.perf_counter() - t0, 3)

        self.warnings = []
        max_requirements = get_config().max_requirements
        if len(sentences) > max_requirements:
            self.warnings.append(
                f"Tài liệu có {len(sentences)} câu yêu cầu; chỉ {max_requirements} câu đầu tiên "
                "được phân tích để bảo vệ tài nguyên hệ thống."
            )
            sentences = sentences[:max_requirements]

        # Khởi tạo thông tin dự án: ưu tiên tên nhập tay, hoặc trích xuất chính xác tên hệ thống trong BRD
        fallback_file_title = filename.rsplit(".", 1)[0] if "." in filename else "Dự án Mới"
        extracted_sys_name = RequirementSegmenter.extract_system_title(raw_text, fallback_file_title)
        p_name = project_name or extracted_sys_name
        self.current_project = ProjectDTO(
            project_id=f"PROJ-{uuid.uuid4().hex}",
            project_name=p_name,
            source_filename=filename,
            language=lang,
            owner_id=self.owner_id,
        )
        self.db.save_project(self.current_project)

        # Bước 2: Phân loại FR / NFR lai ghép
        if progress_callback:
            progress_callback(
                2,
                "HYBRID CLASSIFIER",
                f"Định tuyến phân loại FR/NFR & ISO 25010 cho {len(sentences)} câu yêu cầu...",
            )
        t1 = time.perf_counter()
        classified_reqs = self.classifier.classify(sentences, lang=lang)
        for req in classified_reqs:
            req.project_id = self.current_project.project_id
        timings["classification_sec"] = round(time.perf_counter() - t1, 3)

        # Bước 3: Rà soát mơ hồ & gợi ý chuẩn SMART
        if progress_callback:
            progress_callback(3, "AMBIGUITY & SMART", "Quét từ điển cảm tính, kiểm tra Actor/Metric & tổng hợp câu SMART...")
        t2 = time.perf_counter()
        analyzed_reqs = self.ambiguity_detector.analyze_batch(classified_reqs, lang=lang)
        self.current_requirements = analyzed_reqs
        self.db.save_requirements(self.current_requirements)
        timings["ambiguity_and_smart_sec"] = round(time.perf_counter() - t2, 3)

        # Bước 4: Sinh Agile User Stories & Tiêu chí Nghiệm thu Gherkin
        if progress_callback:
            progress_callback(4, "BDD GENERATOR", "Kiến tạo Agile User Stories (Role-Goal-Benefit) & kịch bản Gherkin...")
        t3 = time.perf_counter()
        stories = self.user_story_gen.generate_stories_batch(self.current_requirements, lang=lang)
        self.current_user_stories = stories
        self._persist_user_stories()
        timings["user_stories_gen_sec"] = round(time.perf_counter() - t3, 3)

        # Bước 5: Sinh mã PlantUML và kết xuất sơ đồ Use Case
        if progress_callback:
            progress_callback(5, "UML 2.5 & IEEE 830", "Biên dịch sơ đồ Use Case PlantUML & đóng gói hồ sơ đặc tả SRS...")
        t4 = time.perf_counter()
        puml_code, puml_bytes = self.plantuml_exporter.export(
            self.current_user_stories,
            system_title=self.current_project.project_name,
            requirements=self.current_requirements,
        )
        self.current_plantuml_code = puml_code
        self.current_plantuml_bytes = puml_bytes
        timings["plantuml_export_sec"] = round(time.perf_counter() - t4, 3)

        timings["total_execution_sec"] = round(time.perf_counter() - total_start, 3)
        self.timings = timings
        if progress_callback:
            progress_callback(6, "COMPLETED", f"Hoàn tất toàn bộ đường ống trong {self.timings['total_execution_sec']}s")

        return self.get_current_result()

    def get_current_result(self) -> AnalysisResultDTO:
        """Lấy đối tượng AnalysisResultDTO đồng bộ mới nhất."""
        return AnalysisResultDTO(
            project=self.current_project,
            requirements=self.current_requirements,
            user_stories=self.current_user_stories,
            plantuml_code=self.current_plantuml_code,
            plantuml_image_bytes=self.current_plantuml_bytes,
            timings=self.timings,
            warnings=self.warnings,
        )

    def apply_smart_rewrite(self, req_id: str, new_text: Optional[str] = None):
        """Thao tác Human-in-the-Loop: Áp dụng câu viết lại SMART cho một yêu cầu."""
        for req in self.current_requirements:
            if req.req_id == req_id:
                if new_text:
                    req.raw_text = new_text
                elif req.smart_rewrite:
                    req.raw_text = req.smart_rewrite

                req.is_ambiguous = False
                req.vague_terms = []
                req.missing_actor = False
                req.missing_metric = False
                break

        self.db.save_requirements(self.current_requirements)
        self.resync_artifacts()

    def update_requirement_type(self, req_id: str, new_type: str, new_category: Optional[str] = None):
        """Thao tác Human-in-the-Loop: Đổi nhãn FR / NFR thủ công."""
        for req in self.current_requirements:
            if req.req_id == req_id:
                req.req_type = new_type
                req.nfr_category = new_category if new_type == "NFR" else None
                break

        self.db.save_requirements(self.current_requirements)
        self.resync_artifacts()

    def _persist_user_stories(self):
        if self.current_project:
            for story in self.current_user_stories:
                story.project_id = self.current_project.project_id
        self.db.save_user_stories(self.current_user_stories)

    def resync_artifacts(self):
        """Đồng bộ lại User Stories, PlantUML sau khi người dùng chỉnh sửa."""
        if not self.current_project or not self.current_requirements:
            return

        lang = self.current_project.language
        self.current_user_stories = self.user_story_gen.generate_stories_batch(
            self.current_requirements, lang=lang
        )
        self._persist_user_stories()

        self.current_plantuml_code, self.current_plantuml_bytes = self.plantuml_exporter.export(
            self.current_user_stories,
            system_title=self.current_project.project_name,
            requirements=self.current_requirements,
        )

    def export_srs_docx(self) -> bytes:
        """Xuất bản tài liệu Word (.docx)."""
        builder = SRSBuilder()
        builder.set_project(self.current_project)
        builder.set_requirements(self.current_requirements)
        builder.set_user_stories(self.current_user_stories)
        return builder.export_docx()

    def export_srs_markdown(self) -> str:
        """Xuất bản tài liệu Markdown (.md)."""
        builder = SRSBuilder()
        builder.set_project(self.current_project)
        builder.set_requirements(self.current_requirements)
        builder.set_user_stories(self.current_user_stories)
        return builder.export_markdown()

    def export_jira_csv(self, project_key: str = "PROJ") -> str:
        """Xuất tệp CSV định dạng chuẩn Jira Issue Import."""
        from src.integrations.jira_sync import JiraSync
        return JiraSync.generate_import_csv(self.current_user_stories, project_key=project_key)

    def export_github_json(self) -> str:
        """Xuất danh sách User Stories định dạng JSON cho GitHub."""
        from src.integrations.github_sync import GitHubIssueSync
        return GitHubIssueSync.generate_export_json(self.current_user_stories)

    def export_trello_json(self, board_name: Optional[str] = None) -> str:
        """Xuất cấu trúc Trello Board dạng JSON."""
        from src.integrations.trello_sync import TrelloSync
        b_name = board_name or (self.current_project.project_name if self.current_project else "BA-Gen Backlog")
        return TrelloSync.generate_board_json(self.current_user_stories, board_name=b_name)

    def sync_to_github(self, repo: str, token: str) -> dict:
        """Đồng bộ tạo GitHub Issues trực tiếp qua API."""
        from src.integrations.github_sync import GitHubIssueSync
        return GitHubIssueSync.sync_to_github_api(repo, token, self.current_user_stories)

    def sync_to_jira(self, domain: str, email: str, token: str, project_key: str) -> dict:
        """Đồng bộ tạo Jira Issues trực tiếp qua API."""
        from src.integrations.jira_sync import JiraSync
        return JiraSync.sync_to_jira_api(domain, email, token, project_key, self.current_user_stories)

    def sync_to_trello(self, api_key: str, token: str, list_id: str) -> dict:
        """Đồng bộ tạo Trello Cards trực tiếp qua API."""
        from src.integrations.trello_sync import TrelloSync
        return TrelloSync.sync_to_trello_api(api_key, token, list_id, self.current_user_stories)
