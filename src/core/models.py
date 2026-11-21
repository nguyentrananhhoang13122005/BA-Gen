"""Lược đồ dữ liệu Pydantic (DTOs) cho hệ thống BA-Gen (ReqAssist-NLP).

Định nghĩa các cấu trúc dữ liệu nghiêm ngặt cho Dự án, Yêu cầu (FR/NFR),
User Stories, Tiêu chí Nghiệm thu (Gherkin) và Hợp đồng phản hồi LLM.
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectDTO(BaseModel):
    """Thông tin tổng quan về phiên phân tích bài toán."""
    project_id: str
    project_name: str
    source_filename: str
    language: str = Field(default="vi", description="Ngôn ngữ chính: 'vi' hoặc 'en'")
    owner_id: Optional[str] = Field(default=None, description="ID phiên sở hữu dự án")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AcceptanceCriteriaDTO(BaseModel):
    """Tiêu chí nghiệm thu theo cú pháp Gherkin chuẩn BDD."""
    scenario: str
    given: str
    when: str
    then: str


class UserStoryDTO(BaseModel):
    """Agile User Story theo mẫu Role - Goal - Benefit kèm Gherkin ACs."""
    story_id: str
    req_id: str
    project_id: str = "default_project"
    role: str
    goal: str
    benefit: str
    acceptance_criteria: List[AcceptanceCriteriaDTO] = Field(default_factory=list)
    puml_usecase_name: str = ""


class RequirementDTO(BaseModel):
    """Mô hình dữ liệu chi tiết của từng câu yêu cầu."""
    req_id: str
    project_id: str = "default_project"
    raw_text: str
    req_type: str = Field(default="FR", description="'FR' hoặc 'NFR'")
    nfr_category: Optional[str] = Field(
        default=None,
        description="ISO/IEC 25010: Performance, Security, Usability, Reliability, Maintainability, Portability",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_ambiguous: bool = False
    vague_terms: List[str] = Field(default_factory=list)
    missing_actor: bool = False
    missing_metric: bool = False
    smart_rewrite: Optional[str] = None


class BatchClassificationItem(BaseModel):
    """Phần tử đơn lẻ trong phản hồi phân loại batch của LLM."""
    index: int
    req_type: str
    nfr_category: Optional[str] = None
    confidence: float = 0.9
    reasoning: Optional[str] = None


class BatchClassificationResponse(BaseModel):
    """Phản hồi JSON có cấu trúc cho batch phân loại FR/NFR."""
    batch_results: List[BatchClassificationItem] = Field(default_factory=list)


class AnalysisResultDTO(BaseModel):
    """Kết quả tổng thể sau quy trình phân tích của RequirementAnalysisFacade."""
    project: ProjectDTO
    requirements: List[RequirementDTO] = Field(default_factory=list)
    user_stories: List[UserStoryDTO] = Field(default_factory=list)
    plantuml_code: str = ""
    plantuml_image_bytes: Optional[bytes] = None
    timings: dict = Field(default_factory=dict)
