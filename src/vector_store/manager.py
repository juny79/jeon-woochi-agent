import chromadb
from typing import List
from src.common.schema import Document
from openai import OpenAI

class VectorDBManager:
    def __init__(self, api_key: str, db_path: str):
        # Solar 임베딩을 사용하기 위한 클라이언트 설정
        self.client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1/solar")
        self.db_client = chromadb.PersistentClient(path=db_path)
        self.collection = self.db_client.get_or_create_collection("woochi_knowledge")

    def get_embedding(self, text: str) -> List[float]:
        """Solar Embedding API를 사용하여 벡터 변환"""
        response = self.client.embeddings.create(
            model="embedding-query", # 또는 'embedding-passage'
            input=text
        )
        return response.data[0].embedding

    def add_documents(self, docs: List[Document]):
        """문서를 벡터화하여 ChromaDB에 저장"""
        for doc in docs:
            embedding = self.get_embedding(doc.content)
            self.collection.add(
                ids=[doc.doc_id],
                embeddings=[embedding],
                metadatas=[doc.metadata],
                documents=[doc.content]
            )
        print(f"허허, {len(docs)}개의 지식을 내 도술 주머니(DB)에 담았소.")