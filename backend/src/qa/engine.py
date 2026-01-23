from typing import List
from src.llm.client import SolarClient
from src.common.schema import Document

class QAEngine:
    """하이브리드 리트리버와 연동되는 답변 엔진"""
    def __init__(self, retriever, api_key: str):
        self.retriever = retriever
        self.llm_client = SolarClient(api_key=api_key)

    def get_answer(self, question: str) -> dict:
        # 1. 하이브리드 검색 실행
        print(f"   [QA] 검색 시작: {question}")
        retrieved_docs = self.retriever.retrieve(question)
        print(f"   [QA] {len(retrieved_docs)}개 문서 검색됨")
        
        if not retrieved_docs:
            return {
                "answer": "허허, 내 지식 주머니(Context)에 그에 관한 기록이 없구려.",
                "sources": []
            }

        # 2. 참고 지식 구성
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            context_parts.append(f"[비급서 {i+1}권]: {doc.page_content}")
        
        context_text = "\n\n".join(context_parts)
        sources = [doc.metadata.get("source_url", "unknown") for doc in retrieved_docs]

        # 3. 프롬프트 구성
        prompt = [
            {"role": "system", "content": (
                "당신은 명상과 영혼의 전문가 '전우치'요. "
                "아래 제공된 [참고한 비급서]의 내용을 바탕으로 질문에 답하시오. "
                "비급서에 없는 정보는 지어내지 말고 솔직히 모른다고 답하시오.\n\n"
                "### 답변 가독성 규칙:\n"
                "1. **제목과 소제목**: 대분류는 '###'를, 중간 분류는 '####'를 사용하여 가독성을 높이시오.\n"
                "2. **목록 지향**: 설명은 가능한 한 글머리 기호('-' 또는 '1.')를 사용하여 구분하시오.\n"
                "3. **핵심 강조**: 중요한 단어나 문장은 반드시 **두껍게** 표시하시오.\n"
                "4. **여백**: 문단 사이에는 충분한 줄바꿈을 두어 답답하지 않게 하시오.\n"
                "5. **출처 언급**: 답변 시 어느 비급서를 참고했는지 자연스럽게 언급하시오(예: 비급서 1권에 따르면~)."
            )},
            {"role": "user", "content": f"[참고한 비급서]\n{context_text}\n\n[질문]\n{question}"}
        ]

        # 4. 답변 생성
        print("   [QA] LLM 호출 중...")
        answer = self.llm_client.generate(prompt)
        print(f"   [QA] 답변 생성됨")

        return {
            "answer": answer,
            "sources": list(set(sources))
        }

    def get_answer_stream(self, question: str):
        """스트리밍 방식으로 답변을 생성하오."""
        # 1. 하이브리드 검색 실행
        print(f"   [QA/Stream] 검색 시작: {question}")
        retrieved_docs = self.retriever.retrieve(question)
        
        if not retrieved_docs:
            yield "허허, 내 지식 주머니(Context)에 그에 관한 기록이 없구려."
            return

        # 2. 참고 지식 구성
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            context_parts.append(f"[비급서 {i+1}권]: {doc.page_content}")
        
        context_text = "\n\n".join(context_parts)

        # 3. 프롬프트 구성
        prompt = [
            {"role": "system", "content": (
                "당신은 명상과 영혼의 전문가 '전우치'요. "
                "아래 제공된 [참고한 비급서]의 내용을 바탕으로 질문에 답하시오. "
                "비급서에 없는 정보는 지어내지 말고 솔직히 모른다고 답하시오. "
                "반드시 전우치 도사의 말투(~소, ~하오, ~구려)를 사용하시오.\n\n"
                "### 답변 가독성 규칙:\n"
                "1. **제목과 소제목**: 대분류는 '###'를, 중간 분류는 '####'를 사용하여 가독성을 높이시오.\n"
                "2. **목록 지향**: 설명은 가능한 한 글머리 기호('-' 또는 '1.')를 사용하여 구분하시오.\n"
                "3. **핵심 강조**: 중요한 단어나 문장은 반드시 **두껍게** 표시하시오.\n"
                "4. **여백**: 문단 사이에는 충분한 줄바꿈을 두어 답답하지 않게 하시오.\n"
                "5. **출처 언급**: 답변 시 어느 비급서를 참고했는지 자연스럽게 언급하시오(예: 비급서 1권에 따르면~)."
            )},
            {"role": "user", "content": f"[참고한 비급서]\n{context_text}\n\n[질문]\n{question}"}
        ]

        # 4. 답변 스트리밍
        print("   [QA/Stream] LLM 스트리밍 호출 중...")
        for chunk in self.llm_client.stream_generate(prompt):
            yield chunk
