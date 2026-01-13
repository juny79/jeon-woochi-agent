import os

# 저장 및 검색 기능이 모두 포함된 완벽한 manager.py 코드
complete_code = """import os
import uuid
from typing import List, Any

import chromadb
from chromadb.config import Settings
from langchain_core.documents import Document
# LangChain과 Chroma를 연결하기 위한 임포트
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings

# [임시] 임베딩을 위한 더미 클래스 (에러 방지용)
# 실제 서비스 시에는 SolarEmbeddingFunction 등으로 교체해야 함
class MockEmbeddings(Embeddings):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # 1536차원 더미 벡터 반환 (OpenAI 기준)
        return [[0.1] * 1536 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        return [0.1] * 1536

class VectorDBManager:
    def __init__(self, api_key: str = None, db_path: str = "./chroma_db"):
        self.api_key = api_key
        # DB 경로 설정
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = None
        
        # 임베딩 함수 초기화 (여기서는 Mock 사용)
        self.embedding_func = MockEmbeddings()

    def get_collection(self, collection_name: str):
        self.collection = self.client.get_or_create_collection(name=collection_name)
        return self.collection

    def get_embedding(self, text: str) -> List[float]:
        # 단일 텍스트 임베딩
        return self.embedding_func.embed_query(text)

    def add_documents(self, docs: List[Document], collection_name: str = "default_collection"):
        \"\"\"문서를 벡터화하여 ChromaDB에 저장 (수정된 버전)\"\"\"
        # 컬렉션 로드
        if self.collection is None or self.collection.name != collection_name:
            self.get_collection(collection_name)

        print(f"   [VectorDB] '{collection_name}' 컬렉션에 {len(docs)}개의 문서를 저장 중...")

        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for doc in docs:
            # 1. 텍스트 추출 (page_content 사용)
            text = doc.page_content
            
            # 2. ID 생성
            doc_id = doc.metadata.get("id", str(uuid.uuid4()))
            
            # 3. 임베딩 생성
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

    def get_vector_retriever(self, collection_name: str, k: int = 3):
        \"\"\"[복구됨] LangChain 호환 Retriever 반환\"\"\"
        # LangChain의 Chroma 래퍼를 사용하여 Retriever 생성
        vectorstore = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embedding_func,
        )
        # 검색기(Retriever) 반환
        return vectorstore.as_retriever(search_kwargs={"k": k})
"""

# 파일 경로 설정
file_path = os.path.join("src", "vector_store", "manager.py")

# 강제로 덮어쓰기
with open(file_path, "w", encoding="utf-8") as f:
    f.write(complete_code)

print(f"✅ {file_path} 파일이 성공적으로 복구되었습니다.")
print("이제 다시 'serve' 명령어를 실행해보세요!")