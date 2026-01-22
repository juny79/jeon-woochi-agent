from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_upstage import UpstageEmbeddings # 2026년 기준 최신 라이브러리 활용
from src.config import Config

class ChunkerFactory:
    """전략별 청커를 생성하는 공장 클래스"""
    
    @staticmethod
    def get_chunker(strategy: str):
        # Solar 임베딩 모델 설정 (Semantic 전략용)
        embeddings = UpstageEmbeddings(
            api_key=Config.SOLAR_API_KEY, 
            model="embedding-query"
        )

        if strategy == "recursive":
            print("--- [RecursiveCharacterTextSplitter] 가동 ---")
            return RecursiveCharacterTextSplitter(
                chunk_size=Config.CHUNK_SIZE, 
                chunk_overlap=Config.CHUNK_OVERLAP
            )
            
        elif strategy == "semantic":
            print("--- [SemanticChunker] 가동 (Solar Embedding 기반) ---")
            # 의미론적 유사성이 변하는 지점을 찾아 분할
            return SemanticChunker(
                embeddings, 
                breakpoint_threshold_type="percentile"
            )
            
        elif strategy == "heading":
            print("--- [Heading-based Splitter] 가동 ---")
            # 마크다운이나 특정 구조 문서의 헤더를 기준으로 분할
            return RecursiveCharacterTextSplitter(
                separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", " "]
            )
        else:
            raise ValueError(f"허허, '{strategy}'는 아직 연마하지 못한 도술이오.")