"""Lớp điều phối trung tâm RequirementAnalysisFacade theo Facade Pattern.

Đóng vai trò là cổng giao tiếp duy nhất giữa giao diện người dùng Streamlit
và toàn bộ đường ống xử lý 6 bước phía sau. Hỗ trợ thao tác Human-in-the-Loop.
"""

import time
from typing import List, Optional, Union
from src.analyzers.ambiguity_detector import AmbiguityDetector
from src.classifiers.hybrid_classifier import HybridClassifierStrategy
from src.classifiers.llm_client import MultiLLMClient
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
        confidence_threshold: float = 0.75,
        force_llm_mode: bool = False,
    ):
        self.llm_client = llm_client or MultiLLMClient()
        self.db = db_manager or DatabaseManager()
        self.classifier = HybridClassifierStrategy(
            llm_client=self.llm_client,
            db_manager=self.db,
            confidence_threshold=confidence_threshold,
            force_llm_mode=force_llm_mode,
        )
        self.ambiguity_detector = AmbiguityDetector(llm_client=self.llm_client)
        self.user_story_gen = UserStoryGenerator(llm_client=self.llm_client)
        self.plantuml_exporter = PlantUMLExporter()

        # Dữ liệu phiên hiện tại
        self.current_project: Optional[ProjectDTO] = None
        self.current_requirements: List[RequirementDTO] = []
        self.current_user_stories: List[UserStoryDTO] = []
        self.current_plantuml_code: str = ""
        self.current_plantuml_bytes: Optional[bytes] = None
        self.timings: dict = {}

    def analyze_document(
        self,
        source: Union[bytes, str],
        filename: str = "input.txt",
        file_size_bytes: int = 0,
        project_name: Optional[str] = None
    ) -> AnalysisResultDTO:
        """Thực thi đường ống xử lý 6 bước từ tài liệu thô đến bộ đặc tả hoàn chỉnh."""
        total_start = time.perf_counter()
        timings = {}

        # Bước 1: Đọc tệp & tách câu nguyên tử
        t0 = time.perf_counter()
        parser = DocumentIngestionFactory.create_parser(filename, file_size_bytes)
        raw_text = parser.parse(source)
        sentences, lang = RequirementSegmenter.segment(raw_text)
        timings["parsing_and_segmentation_sec"] = round(time.perf_counter() - t0, 3)

        # Khởi tạo thông tin dự án
        p_name = project_name or (filename.rsplit(".", 1)[0] if "." in filename else "Dự án Mới")
        self.current_project = ProjectDTO(
            project_id=f"PROJ-{int(time.time())}",
            project_name=p_name,
            source_filename=filename,
            language=lang
        )
        self.db.save_project(self.current_project)

        # Bước 2: Phân loại FR / NFR lai ghép
        t1 = time.perf_counter()
        classified_reqs = self.classifier.classify(sentences, lang=lang)
        for req in classified_reqs:
            req.project_id = self.current_project.project_id
        timings["classification_sec"] = round(time.perf_counter() - t1, 3)

        # Bước 3: Rà soát mơ hồ & gợi ý chuẩn SMART
        t2 = time.perf_counter()
        analyzed_reqs = self.ambiguity_detector.analyze_batch(classified_reqs, lang=lang)
        self.current_requirements = analyzed_reqs
        self.db.save_requirements(self.current_requirements)
        timings["ambiguity_and_smart_sec"] = round(time.perf_counter() - t2, 3)

        # Bước 4: Sinh Agile User Stories & Tiêu chí Nghiệm thu Gherkin
        t3 = time.perf_counter()
        stories = self.user_story_gen.generate_stories_batch(self.current_requirements, lang=lang)
        self.current_user_stories = stories
        self.db.save_user_stories(self.current_user_stories)
        timings["user_stories_gen_sec"] = round(time.perf_counter() - t3, 3)

        # Bước 5: Sinh mã PlantUML và kết xuất sơ đồ Use Case
        t4 = time.perf_counter()
        puml_code, puml_bytes = self.plantuml_exporter.export(
            self.current_user_stories,
            system_title=self.current_project.project_name
        )
        self.current_plantuml_code = puml_code
        self.current_plantuml_bytes = puml_bytes
        timings["plantuml_export_sec"] = round(time.perf_counter() - t4, 3)

        timings["total_execution_sec"] = round(time.perf_counter() - total_start, 3)
        self.timings = timings

        return AnalysisResultDTO(
            project=self.current_project,
            requirements=self.current_requirements,
            user_stories=self.current_user_stories,
            plantuml_code=self.current_plantuml_code,
            plantuml_image_bytes=self.current_plantuml_bytes,
            timings=self.timings
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

    def resync_artifacts(self):
        """Đồng bộ lại User Stories, PlantUML sau khi người dùng chỉnh sửa."""
        if not self.current_project or not self.current_requirements:
            return

        lang = self.current_project.language
        self.current_user_stories = self.user_story_gen.generate_stories_batch(
            self.current_requirements, lang=lang
        )
        self.db.save_user_stories(self.current_user_stories)

        self.current_plantuml_code, self.current_plantuml_bytes = self.plantuml_exporter.export(
            self.current_user_stories, system_title=self.current_project.project_name
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
