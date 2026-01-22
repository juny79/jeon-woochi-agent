from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from src.qa.engine import QAEngine
from src.agent.persona_prompt import JeonWoochiPersona

class JeonWoochiGraphAgent:
    def __init__(self, qa_engine: QAEngine):
        self.qa_engine = qa_engine
        self.workflow = StateGraph(AgentState)
        
        # 1. 노드 정의 (행동 단위)
        self.workflow.add_node("chatbot", self.call_model)
        self.workflow.add_node("retrieve_knowledge", self.run_rag)
        
        # 2. 엣지 정의 (흐름 제어)
        self.workflow.set_entry_point("chatbot") # 시작점
        
        # 조건부 엣지: 모델이 검색이 필요하다고 판단하면 RAG로, 아니면 종료
        self.workflow.add_conditional_edges(
            "chatbot",
            self.decide_next_step,
            {
                "search": "retrieve_knowledge",
                "end": END
            }
        )
        self.workflow.add_edge("retrieve_knowledge", "chatbot") # 검색 후 다시 답변 생성

        # 3. 컴파일 (실행 가능한 앱으로 변환)
        self.app = self.workflow.compile()

    # --- 노드 함수들 ---
    def call_model(self, state):
        """전우치 페르소나로 답변 생성"""
        messages = state['messages']
        # 시스템 프롬프트가 없다면 추가
        if not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=JeonWoochiPersona.SYSTEM_PROMPT)] + messages
            
        # LLM 호출 (여기서 SolarClient 사용)
        response = self.qa_engine.llm_client.generate(messages) 
        return {"messages": [response]}

    def run_rag(self, state):
        """QA Engine을 도구로 사용"""
        last_user_msg = state['messages'][-1].content
        # 기존에 만든 QA Engine 활용
        rag_result = self.qa_engine.get_answer(last_user_msg)
        
        # 검색 결과를 문맥으로 추가
        return {"messages": [f"[전우치의 지식 주머니]: {rag_result['answer']}"]}

    def decide_next_step(self, state):
        """질문 분석 후 검색 필요 여부 판단 (Router)"""
        last_msg = state['messages'][-1]
        # 간단한 로직: 질문에 '명상', '호흡', '전우치' 등이 있으면 검색
        if "명상" in last_msg.content or "호흡" in last_msg.content:
            return "search"
        return "end"

    # --- 실행 함수 ---
    def chat(self, user_input: str):
        inputs = {"messages": [HumanMessage(content=user_input)]}
        result = self.app.invoke(inputs)
        return result['messages'][-1].content