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
                "아래 제공된 [참고한 비급서]의 내용만을 근거로 답하시오. "
                "비급서에 없는 정보(장소명, 수치, 고유명사 등)는 절대 지어내지 말고, 모른다고 솔직히 밝히시오. "
                "질문에서 명시적으로 묻지 않은 주제(예: 뇌파, 호르몬, 무관한 수행법 등)는 답변에 포함하지 마시오. 질문의 핵심 주제에만 집중하여 답하시오.\n\n"
                "【출력 형식 규칙 — 반드시 준수하시오】\n"
                "① 첫 줄에 인트로 문장을 한 줄만 쓰시오.\n"
                "② 그 다음은 반드시 빈 줄 하나를 삽입하시오.\n"
                "③ 섹션 제목은 '**번호. 제목**' 형식으로 독립된 줄에 쓰시오 (# 기호 사용 금지).\n"
                "④ 제목 바로 다음 줄(빈 줄 없이)에 한 문장 설명을 쓰시오.\n"
                "⑤ 설명 다음 줄부터 '- **키워드**: 설명' 형식으로 항목을 한 줄씩 쓰시오.\n"
                "⑥ 섹션과 섹션 사이에만 빈 줄 하나를 삽입하시오.\n"
                "⑦ 마지막 섹션 뒤에 빈 줄 하나 후 마무리 문장을 한 줄 쓰시오.\n"
                "⑧ 제목·설명·항목을 절대로 한 줄에 이어 붙이지 마시오.\n"
                "⑨ 말투는 '~하오', '~구려', '~소'를 사용하시오.\n"
                "⑩ 영어 사용 금지. 한국어 띄어쓰기 규칙을 준수하시오.\n\n"
                "【예시 — 이 형식 그대로 출력하시오】\n\n"
                "도사가 호흡법 두 가지를 전하겠소.\n\n"
                "**1. 4-7-8 호흡법**\n"
                "초심자도 쉽게 따라 할 수 있는 기본 호흡법이오.\n"
                "- **방법**: 4초 코로 들이쉬고, 7초 참은 뒤, 8초에 걸쳐 입으로 내쉬시오.\n"
                "- **효과**: 부교감 신경을 활성화하여 불안과 긴장을 해소할 수 있소.\n"
                "- **주의**: 어지러움을 느끼면 즉시 중단하시오.\n\n"
                "**2. 역복식 호흡법**\n"
                "내장 기능을 다스리는 도가의 비전 호흡법이오.\n"
                "- **방법**: 들숨에 배를 안으로 당기고, 날숨에 배를 바깥으로 밀어내시오.\n"
                "- **효과**: 내장을 자극하고 소화 기능을 높일 수 있소.\n\n"
                "그대의 수련이 날로 깊어지길 바라오."
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
        print(f"   [QA/Stream] 검색됨: {len(retrieved_docs)}개 문서")
        
        if not retrieved_docs:
            yield "허허, 내 지식 주머니(Context)에 그에 관한 기록이 없구려."
            return

        # 2. 참고 지식 구성
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            content = doc.page_content[:500] if len(doc.page_content) > 500 else doc.page_content
            context_parts.append(f"[문서 {i+1}]: {content}")
        
        context_text = "\n\n".join(context_parts)
        print(f"   [QA/Stream] 컨텍스트 길이: {len(context_text)}자")

        # 3. 프롬프트 구성 - 가독성 높은 포맷 강조
        system_prompt = (
            "당신은 명상 전문 도사 '전우치'입니다. "
            "반드시 아래 [참고 자료]에 있는 내용만을 근거로 답하시오. "
            "참고 자료에 없는 정보(장소명, 수치, 고유명사 등)는 절대 지어내지 말고, 모른다고 솔직히 밝히시오. "
            "질문에서 명시적으로 묻지 않은 주제(예: 뇌파, 호르몬, 무관한 수행법 등)는 답변에 포함하지 마시오. 질문의 핵심 주제에만 집중하여 답하시오.\n\n"
            "【출력 형식 규칙 — 반드시 준수하시오】\n"
            "① 첫 줄에 인트로 문장을 한 줄만 쓰시오.\n"
            "② 그 다음은 반드시 빈 줄 하나를 삽입하시오.\n"
            "③ 섹션 제목은 '**번호. 제목**' 형식으로 독립된 줄에 쓰시오 (# 기호 사용 금지).\n"
            "④ 제목 바로 다음 줄(빈 줄 없이)에 한 문장 설명을 쓰시오.\n"
            "⑤ 설명 다음 줄부터 '- **키워드**: 설명' 형식으로 항목을 한 줄씩 쓰시오.\n"
            "⑥ 섹션과 섹션 사이에만 빈 줄 하나를 삽입하시오.\n"
            "⑦ 마지막 섹션 뒤에 빈 줄 하나 후 마무리 문장을 한 줄 쓰시오.\n"
            "⑧ 제목·설명·항목을 절대로 한 줄에 이어 붙이지 마시오.\n"
            "⑨ 말투는 '~하오', '~구려', '~소'를 사용하시오.\n"
            "⑩ 영어 사용 금지. 한국어 띄어쓰기 규칙을 준수하시오.\n\n"
            "【예시 — 이 형식 그대로 출력하시오】\n\n"
            "도사가 호흡법 두 가지를 전하겠소.\n\n"
            "**1. 4-7-8 호흡법**\n"
            "초심자도 쉽게 따라 할 수 있는 기본 호흡법이오.\n"
            "- **방법**: 4초 코로 들이쉬고, 7초 참은 뒤, 8초에 걸쳐 입으로 내쉬시오.\n"
            "- **효과**: 부교감 신경을 활성화하여 불안과 긴장을 해소할 수 있소.\n"
            "- **주의**: 어지러움을 느끼면 즉시 중단하시오.\n\n"
            "**2. 역복식 호흡법**\n"
            "내장 기능을 다스리는 도가의 비전 호흡법이오.\n"
            "- **방법**: 들숨에 배를 안으로 당기고, 날숨에 배를 바깥으로 밀어내시오.\n"
            "- **효과**: 내장을 자극하고 소화 기능을 높일 수 있소.\n\n"
            "그대의 수련이 날로 깊어지길 바라오."
        )
        
        user_content = (
            f"참고 자료:\n{context_text}\n\n"
            f"질문: {question}\n\n"
            f"답변:"
        )
        
        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        print(f"   [QA/Stream] 프롬프트 준비 완료. 시스템 메시지: {len(system_prompt)}자, 사용자 메시지: {len(user_content)}자")

        # 4. 답변 스트리밍
        print("   [QA/Stream] LLM 스트리밍 호출 중...")
        chunk_count = 0
        for chunk in self.llm_client.stream_generate(prompt):
            chunk_count += 1
            if chunk_count % 10 == 0:
                print(f"   [QA/Stream] 청크 {chunk_count}개 수신...")
            yield chunk
        print(f"   [QA/Stream] 완료. 총 {chunk_count}개 청크 전송")
