from typing import List
from src.llm.client import SolarClient
from src.common.schema import Document

class QAEngine:
    """하이브리드 리트리버와 연동되는 답변 엔진"""
    def __init__(self, retriever, api_key: str):
        self.retriever = retriever
        self.llm_client = SolarClient(api_key=api_key)

    def get_answer(self, question: str) -> dict:
        # 1. 하이브리드 검색 실행 (HybridRetriever.retrieve 호출)
        # 결과는 LangChain Document 리스트로 반환됨
        retrieved_docs = self.retriever.retrieve(question)
        
        if not retrieved_docs:
            return {
                "answer": "허허, 내 지식 주머니(Context)에 그에 관한 기록이 없구려.",
                "sources": []
            }

        # 2. Context 구성
        context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])
        sources = [doc.metadata.get("source_url", "unknown") for doc in retrieved_docs]

        # 3. 프롬프트 구성 (System Prompt는 Agent에서 관리하지만, 여기선 QA 전용 프롬프트 사용)
        prompt = [
            {"role": "system", "content": (
                "당신은 명상과 영혼의 전문가 '전우치'요. "
                "아래 제공된 [Context]만을 근거로 하여 질문에 답하시오. "
                "근거가 없다면 솔직히 모른다고 답하고, 지어내지 마시오."
            )},
            {"role": "user", "content": f"[Context]\n{context_text}\n\n[Question]\n{question}"}
        ]

        # 4. 답변 생성
        answer = self.llm_client.generate(prompt)

        return {
            "answer": answer,
            "sources": list(set(sources)) # 중복 제거
        }