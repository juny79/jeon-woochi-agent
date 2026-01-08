class JeonWoochiAgent:
    """페르소나 유지 및 워크플로우 제어 (인격/도구 관리)"""
    def __init__(self, persona, qa_engine):
        self.persona = persona
        self.qa_engine = qa_engine # QA Engine을 도구로 보유
        self.memory = ConversationMemory()

    def chat(self, user_input: str):
        # 1. 질문의 의도 분석 (도술/명상 정보가 필요한가? 아니면 단순 잡담인가?)
        # 2. 정보가 필요하면 self.qa_engine.answer() 호출
        # 3. 결과를 전우치의 말투로 변환하여 출력
        pass