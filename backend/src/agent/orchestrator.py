from src.qa.engine import QAEngine


class ConversationBufferMemory:
    """간단한 대화 메모리 저장소"""
    def __init__(self, memory_key: str = "history", human_prefix: str = "User", ai_prefix: str = "AI"):
        self.memory_key = memory_key
        self.human_prefix = human_prefix
        self.ai_prefix = ai_prefix
        self.buffer = []
    
    def save_context(self, inputs: dict, outputs: dict):
        """사용자 입력과 AI 응답을 메모리에 저장"""
        if "input" in inputs and "output" in outputs:
            self.buffer.append({
                "user": inputs["input"],
                "ai": outputs["output"]
            })
    
    def get_buffer(self) -> str:
        """메모리 버퍼를 문자열로 반환"""
        messages = []
        for item in self.buffer:
            messages.append(f"{self.human_prefix}: {item['user']}")
            messages.append(f"{self.ai_prefix}: {item['ai']}")
        return "\n".join(messages)


class JeonWoochiAgent:
    """페르소나 유지 및 워크플로우 제어 (인격/도구 관리)"""
    def __init__(self, persona, qa_engine: QAEngine):
        self.persona = persona
        self.qa_engine = qa_engine # QA Engine을 도구로 보유
        self.memory = ConversationBufferMemory(memory_key="history", human_prefix="User", ai_prefix="전우치")

    def chat(self, user_input: str) -> str:
        """사용자 입력을 받아 QA Engine으로 답변 생성"""
        try:
            # QA Engine을 통해 답변 생성
            result = self.qa_engine.get_answer(user_input)
            answer = result.get("answer", "허허, 뭔가 이상한데?")
            
            # 메모리에 저장
            self.memory.save_context({"input": user_input}, {"output": answer})
            
            return answer
        except Exception as e:
            return f"오류: {str(e)}"

    def chat_stream(self, user_input: str):
        """사용자 입력을 받아 스트리밍으로 답변 생성"""
        try:
            # QA Engine의 스트리밍 답변 사용
            full_response = ""
            for chunk in self.qa_engine.get_answer_stream(user_input):
                full_response += chunk
                yield chunk
            
            # 최종 답변을 메모리에 저장
            self.memory.save_context({"input": user_input}, {"output": full_response})
            
        except Exception as e:
            yield f"도술 실행 중 오류가 발생했소: {str(e)}"
