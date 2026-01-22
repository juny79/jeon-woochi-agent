from abc import ABC, abstractmethod
from typing import List
from src.common.schema import Document

class BaseCrawler(ABC):
    """모든 크롤러의 부모 클래스"""
    @abstractmethod
    def fetch_data(self, query: str) -> List[Document]:
        """데이터 수집 실행"""
        pass

class TextCleaner:
    """텍스트 정제 전담 클래스"""
    @staticmethod
    def clean(text: str) -> str:
        import re
        # HTML 태그 제거 및 연속된 공백 처리
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()