#!/usr/bin/env python
"""명상소 테스트 스크립트"""
import sys
sys.path.insert(0, '.')

from src.config import Config
from src.vector_store.manager import VectorDBManager
from src.retriever.hybrid_retriever import HybridRetriever
from src.qa.engine import QAEngine
from src.agent.orchestrator import JeonWoochiAgent
from src.agent.persona_prompt import JeonWoochiPersona

def test_qa_engine():
    """QA Engine 테스트"""
    print("=" * 60)
    print("[테스트] QA Engine 및 Orchestrator")
    print("=" * 60)
    
    # 1. DB 매니저 초기화
    db_manager = VectorDBManager(api_key=Config.SOLAR_API_KEY, db_path=Config.DB_PATH)
    collection_name = "meditation_recursive"
    
    # 2. 하이브리드 리트리버 생성
    print("\n[1단계] 하이브리드 리트리버 생성...")
    try:
        hybrid_retriever = HybridRetriever(db_manager=db_manager, collection_name=collection_name)
        print("[OK] 리트리버 생성 성공")
    except Exception as e:
        print(f"[FAIL] 리트리버 생성 실패: {e}")
        return
    
    # 3. QA Engine 생성
    print("\n[2단계] QA Engine 생성...")
    try:
        qa_engine = QAEngine(retriever=hybrid_retriever, api_key=Config.SOLAR_API_KEY)
        print("[OK] QA Engine 생성 성공")
    except Exception as e:
        print(f"[FAIL] QA Engine 생성 실패: {e}")
        return
    
    # 4. Agent 생성
    print("\n[3단계] JeonWoochiAgent 생성...")
    try:
        persona = JeonWoochiPersona.SYSTEM_PROMPT
        agent = JeonWoochiAgent(persona=persona, qa_engine=qa_engine)
        print("[OK] Agent 생성 성공")
    except Exception as e:
        print(f"[FAIL] Agent 생성 실패: {e}")
        return
    
    # 5. 테스트 질문
    print("\n[4단계] 테스트 질문 실행...")
    test_questions = [
        "명상이란 뭐야?",
        "스트레스를 어떻게 줄여?",
        "요가와 명상의 차이는?"
    ]
    
    for q in test_questions:
        print(f"\n>>> 질문: {q}")
        try:
            response = agent.chat(q)
            print(f"[답변]\n{response}\n")
        except Exception as e:
            print(f"[ERROR] {e}\n")

if __name__ == "__main__":
    test_qa_engine()
