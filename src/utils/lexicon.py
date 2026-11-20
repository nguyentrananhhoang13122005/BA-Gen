"""Quản lý nạp từ điển mơ hồ, danh sách Actor và đơn vị đo theo Singleton Pattern.

Đảm bảo tệp JSON chỉ được đọc và nạp vào RAM một lần duy nhất trong suốt
vòng đời của ứng dụng.
"""

import json
import os
import re
from typing import List, Optional


class NLPLexiconManager:
    """Singleton quản lý từ điển mơ hồ, tác nhân và chỉ số đo lường."""

    _instance: Optional["NLPLexiconManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(NLPLexiconManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, lexicon_path: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return

        if lexicon_path is None:
            # Tìm đường dẫn mặc định từ vị trí thư mục hiện tại
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            lexicon_path = os.path.join(base_dir, "data", "ambiguity_lexicon.json")

        self.lexicon_path = lexicon_path
        self.ambiguous_vi: List[str] = []
        self.ambiguous_en: List[str] = []
        self.actors_vi: List[str] = []
        self.actors_en: List[str] = []
        self.metrics_regex: List[re.Pattern] = []

        self._load_lexicon()
        self._initialized = True

    def _load_lexicon(self):
        """Đọc và biên dịch các mẫu Regex từ tệp JSON."""
        if not os.path.exists(self.lexicon_path):
            return

        with open(self.lexicon_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.ambiguous_vi = [term.lower().strip() for term in data.get("ambiguous_terms_vi", [])]
        self.ambiguous_en = [term.lower().strip() for term in data.get("ambiguous_terms_en", [])]
        self.actors_vi = [actor.lower().strip() for actor in data.get("actors_vi", [])]
        self.actors_en = [actor.lower().strip() for actor in data.get("actors_en", [])]

        raw_patterns = data.get("metrics_regex", [])
        self.metrics_regex = [re.compile(p, re.IGNORECASE) for p in raw_patterns]

    def get_ambiguous_terms(self, lang: str = "vi") -> List[str]:
        return self.ambiguous_vi if lang == "vi" else self.ambiguous_en

    def get_actors(self, lang: str = "vi") -> List[str]:
        return self.actors_vi if lang == "vi" else self.actors_en

    def has_metric(self, text: str) -> bool:
        """Kiểm tra câu có chứa số liệu kèm đơn vị định lượng hợp lệ hay không."""
        for pattern in self.metrics_regex:
            if pattern.search(text):
                return True
        return False
