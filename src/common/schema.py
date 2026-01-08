from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class Document:
    """프로젝트 전체에서 사용될 공통 문서 규격"""
    doc_id: str             # 문서 고유 ID (해시값 등)
    title: str              # 제목
    content: str            # 정제된 텍스트 본문
    source_url: str         # 출처 URL
    metadata: Dict = field(default_factory=dict) # 저자, 작성일, 카테고리 등