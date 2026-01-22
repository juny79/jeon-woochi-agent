import os
import uuid
import pickle
from typing import List, Any

import chromadb
from chromadb.config import Settings
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
from rank_bm25 import BM25Okapi
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

# [임시] 임베딩을 위한 더미 클래스
class MockEmbeddings(Embeddings):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * 1536 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        return [0.1] * 1536


class BM25Retriever(BaseRetriever):
    """BM25 기반 키워드 검색 리트리버"""
    
    docs: List[Document] = Field(description="검색할 Document 객체 리스트")
    k: int = Field(default=3, description="반환할 상위 문서 개수")
    bm25: BM25Okapi = Field(exclude=True, default=None)
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, docs: List[Document], k: int = 3):
        """
        BM25 리트리버 초기화
        
        Args:
            docs: 검색할 Document 객체 리스트
            k: 반환할 상위 문서 개수
        """
        # 문서 텍스트를 토큰화하여 BM25 인덱스 생성
        corpus = [doc.page_content.split() for doc in docs]
        bm25 = BM25Okapi(corpus)
        
        super().__init__(docs=docs, k=k, bm25=bm25)
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """BM25를 사용하여 관련 문서 검색"""
        if not self.bm25 or not self.docs:
            return []
        
        query_tokens = query.split()
        scores = self.bm25.get_scores(query_tokens)
        
        # 상위 k개의 인덱스 추출
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:self.k]
        
        return [self.docs[i] for i in top_indices if scores[i] > 0]
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """LangChain BaseRetriever와 호환되는 메서드"""
        return self._get_relevant_documents(query)

class VectorDBManager:
    def __init__(self, api_key: str = None, db_path: str = "./chroma_db"):
        self.api_key = api_key
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = None
        self.embedding_func = MockEmbeddings()
        self.stored_docs = {}  # collection_name -> List[Document] 매핑

    def get_collection(self, collection_name: str):
        self.collection = self.client.get_or_create_collection(name=collection_name)
        return self.collection

    def get_embedding(self, text: str) -> List[float]:
        return self.embedding_func.embed_query(text)

    def add_documents(self, docs: List[Document], collection_name: str = "default_collection"):
        """문서를 벡터화하여 ChromaDB에 저장"""
        if self.collection is None or self.collection.name != collection_name:
            self.get_collection(collection_name)

        print(f"   [VectorDB] '{collection_name}' 컬렉션에 {len(docs)}개의 문서를 저장 중...")

        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for doc in docs:
            text = doc.page_content
            doc_id = doc.metadata.get("id", str(uuid.uuid4()))
            emb = self.get_embedding(text)
            
            ids.append(doc_id)
            embeddings.append(emb)
            metadatas.append(doc.metadata)
            documents.append(text)
            
        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
        print("   [VectorDB] 저장 완료!")
        
        # BM25를 위해 문서를 메모리에 저장
        self.stored_docs[collection_name] = docs

    def get_vector_retriever(self, collection_name: str, k: int = 3):
        """[중요] 검색기 반환 함수"""
        vectorstore = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embedding_func,
        )
        return vectorstore.as_retriever(search_kwargs={"k": k})
    
    def get_bm25_retriever(self, collection_name: str = "default_collection", k: int = 3):
        """BM25 기반 검색기 반환 함수"""
        # 먼저 메모리에 있는 문서 확인
        if collection_name in self.stored_docs:
            docs = self.stored_docs[collection_name]
            if docs:
                return BM25Retriever(docs=docs, k=k)
        
        # 메모리에 없으면 ChromaDB에서 로드
        try:
            collection = self.client.get_collection(name=collection_name)
            all_items = collection.get()  # 모든 문서 조회
            
            if not all_items or not all_items.get('documents'):
                return None
            
            # ChromaDB 데이터를 Document 객체로 변환
            docs = []
            for doc_text, metadata in zip(all_items['documents'], all_items.get('metadatas', [])):
                doc = Document(page_content=doc_text, metadata=metadata or {})
                docs.append(doc)
            
            # 메모리에 캐시
            self.stored_docs[collection_name] = docs
            
            return BM25Retriever(docs=docs, k=k)
        except Exception as e:
            print(f"   [BM25] {collection_name} 컬렉션을 찾을 수 없소: {e}")
            return None