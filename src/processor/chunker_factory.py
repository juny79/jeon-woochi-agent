from langchain.text_splitter import RecursiveCharacterTextSplitter
# SemanticChunker 등 필요한 라이브러리 추가

class ChunkerFactory:
    @staticmethod
    def get_chunker(strategy: str):
        if strategy == "recursive":
            return RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        elif strategy == "heading":
            # 마크다운 헤더 기반 분할 로직 (정책 문서 등에 유리)
            return RecursiveCharacterTextSplitter(separators=["\n# ", "\n## "])
        else:
            raise ValueError(f"허허, '{strategy}'라는 도술(전략)은 아직 배우지 못했소.")