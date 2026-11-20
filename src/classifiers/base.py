"""Giao diện chiến lược phân loại FR/NFR theo Strategy Pattern."""

from abc import ABC, abstractmethod
from typing import List
from src.core.models import RequirementDTO


class IClassifierStrategy(ABC):
    """Giao diện chuẩn cho tất cả các bộ phân loại yêu cầu."""

    @abstractmethod
    def classify(self, sentences: List[str], lang: str = "vi") -> List[RequirementDTO]:
        """Phân loại danh sách câu thành FR hoặc NFR kèm độ tin cậy và nhóm phụ NFR."""
        pass
