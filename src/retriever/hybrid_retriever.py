try:
    from langchain.retrievers import EnsembleRetriever
    _HAS_ENSEMBLE = True
except Exception:
    _HAS_ENSEMBLE = False

from src.vector_store.manager import VectorDBManager


class HybridRetriever:
    """벡터(의미)와 BM25(키워드)를 결합하여 검색 정확도를 높이는 간단한 하이브리드 리트리버.

    런타임에 `langchain.retrievers.EnsembleRetriever`를 사용할 수 없으면
    내부적으로 두 리트리버의 결과를 병합하는 간단한 폴백을 사용하오.
    """

    def __init__(self, db_manager: VectorDBManager, collection_name: str):
        vector_retriever = db_manager.get_vector_retriever(collection_name)
        bm25_retriever = db_manager.get_bm25_retriever(collection_name)

        if bm25_retriever is None:
            raise ValueError("BM25 리트리버가 준비되지 않았구려. 먼저 Ingest를 수행하시오.")

        if _HAS_ENSEMBLE:
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, vector_retriever],
                weights=[0.5, 0.5],
            )
            self._use_ensemble = True
        else:
            # 폴백: 단순 병합 로직 사용
            self._use_ensemble = False
            self._bm25 = bm25_retriever
            self._vector = vector_retriever

    def retrieve(self, query: str):
        """최종 하이브리드 검색 결과를 반환하오."""
        print(f"--- 하이브리드 도술로 '{query}'의 근거를 찾고 있소 ---")
        if self._use_ensemble:
            return self.ensemble_retriever.get_relevant_documents(query)

        # 폴백 병합: BM25 결과 우선으로 두고 중복은 제거하오.
        # VectorStore retriever는 invoke() 또는 get_relevant_documents() 사용
        try:
            bm25_docs = self._bm25.get_relevant_documents(query)
        except Exception:
            bm25_docs = []
        
        try:
            # VectorStoreRetriever는 invoke 메서드 사용
            if hasattr(self._vector, 'get_relevant_documents'):
                vector_docs = self._vector.get_relevant_documents(query)
            elif hasattr(self._vector, 'invoke'):
                vector_docs = self._vector.invoke(query)
            else:
                vector_docs = []
        except Exception:
            vector_docs = []

        seen_ids = set()
        merged = []
        for d in bm25_docs + vector_docs:
            doc_id = getattr(d, 'doc_id', None) or getattr(d, 'id', None)
            key = doc_id or (getattr(d, 'metadata', {}).get('source_url') if hasattr(d, 'metadata') else None)
            if key in seen_ids:
                continue
            seen_ids.add(key)
            merged.append(d)

        return merged