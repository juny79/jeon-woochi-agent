class HybridRetriever:
    """벡터 검색과 키워드 검색을 결합한 고성능 검색기"""
    def __init__(self, vector_store, bm25_retriever):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever

    def retrieve(self, query: str, k: int = 5):
        # [TODO] 벡터 검색 결과와 BM25 결과를 앙상블하여 최적의 근거 추출
        pass