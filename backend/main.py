import os
import argparse
import sys
import subprocess
from threading import Thread
from src.config import Config
from src.crawler.meditation_crawler import MeditationNewsCrawler
from src.processor.chunker_factory import ChunkerFactory
from src.vector_store.manager import VectorDBManager
from src.retriever.hybrid_retriever import HybridRetriever
from src.qa.engine import QAEngine
from src.eval.runner import EvaluationRunner

from src.agent.orchestrator import JeonWoochiAgent # CLI 테스트용
from src.agent.persona_prompt import JeonWoochiPersona
from langchain_core.documents import Document

def start_video_server():
    """비디오 서버를 백그라운드에서 시작"""
    try:
        import time
        # 별도 프로세스로 video_server.py 실행
        thread = Thread(
            target=lambda: subprocess.run(
                [sys.executable, "video_server.py"],
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            ),
            daemon=True
        )
        thread.start()
        time.sleep(1)  # 서버 시작 대기
        print("[VIDEO SERVER] 비디오 서버 시작 (포트 8889)")
    except Exception as e:
        print(f"[ERROR] 비디오 서버 시작 실패: {e}")

def load_markdown_knowledge(file_path: str) -> list[Document]:
    """마크다운 파일을 읽어 LangChain Document 객체 리스트로 반환하오."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        print(f"'{file_path}'에서 전우치의 비급을 읽어들였소.")
        
        # [중요 수정 포인트] 
        # 이전 코드에서 text=text 라고 썼던 부분을 page_content=text 로 수정했습니다.
        # LangChain은 반드시 'page_content'라는 속성을 요구합니다.
        return [Document(page_content=text, metadata={"source": file_path})]
        
    except FileNotFoundError:
        print(f"경고: '{file_path}' 파일이 없소. 빈 손으로 돌아갑니다.")
        return []

def distill_knowledge(docs: list[Document]) -> list[Document]:
    """수집된 날것의 정보를 전우치의 말투와 비급서 형태로 변환하오."""
    from src.llm.client import SolarClient
    client = SolarClient(api_key=Config.SOLAR_API_KEY)
    
    distilled_docs = []
    print(f"--- [DISTILLATION] {len(docs)}개의 지식을 전우치 비급으로 변환 중 ---")
    
    for i, doc in enumerate(docs):
        # 너무 긴 문서는 요약 및 변환
        prompt = [
            {"role": "system", "content": (
                "당신은 조선의 도사 '전우치'이오. 아래 제공된 [Raw Data]를 읽고, "
                "현대인들이 읽기 쉬운 '입문자용 명상/건강 비급' 형태로 재구성하시오. "
                "말투는 반드시 '~하오', '~구려', '~소'와 같은 고풍스러운 도사 말투를 유지하고, "
                "내용은 핵심 위주로 정리하여 '전우치의 비급'처럼 만드시오."
            )},
            {"role": "user", "content": f"[Raw Data]\n{doc.page_content}"}
        ]
        
        try:
            distilled_content = client.generate(prompt)
            # 메타데이터 유지 및 변환 표시
            new_metadata = doc.metadata.copy()
            new_metadata["distilled"] = True
            distilled_docs.append(Document(page_content=distilled_content, metadata=new_metadata))
            print(f"   [{i+1}/{len(docs)}] 변환 완료: {new_metadata.get('title', 'Unknown')}")
        except Exception as e:
            print(f"   [{i+1}/{len(docs)}] 변환 실패, 원본 유지: {e}")
            distilled_docs.append(doc)
            
    return distilled_docs

def run_ingest(args):
    """[팀 A & B] 데이터 적재 모드 (Markdown + News -> Chunk -> Hybrid Indexing)"""
    print(f"--- [INGEST MODE] 전략: {args.strategy} / 하이브리드 적재 시작 ---")
    
    all_docs = []

    # 1. 로컬 마크다운 지식 로드 (우선순위 높음)
    md_docs = load_markdown_knowledge("data/knowledge.md")
    all_docs.extend(md_docs)

    # 2. 뉴스 및 전문 사이트 크롤러 실행
    crawler = MeditationNewsCrawler()
    # 기초 명상 및 STB 고위 수행법 수집
    news_docs = crawler.fetch_data(query="기초 명상 및 건강관리")
    
    # 3. [전우치 도술] 수집된 기초 지식을 전우치 문체로 변환 (Distillation)
    if news_docs:
        distilled_news = distill_knowledge(news_docs)
        all_docs.extend(distilled_news)
    
    if not all_docs:
        print("적재할 지식이 하나도 없구려. 경로를 확인하시오.")
        return

    # 4. 청킹 전략 적용 (Factory)
    chunker = ChunkerFactory.get_chunker(args.strategy)
    chunks = chunker.split_documents(all_docs)
    print(f"총 {len(chunks)}개의 지식 조각으로 나누었소.")
    
    # 5. 저장 (Vector DB + BM25 인덱스 동시 생성)
    db_manager = VectorDBManager(api_key=Config.SOLAR_API_KEY, db_path=Config.DB_PATH)
    collection_name = f"meditation_{args.strategy}"
    
    db_manager.add_documents(chunks, collection_name=collection_name)
    print(f"완료! '{collection_name}' 컬렉션과 BM25 인덱스에 저장되었소.")

def run_eval(args):
    """[팀 C] LangSmith 정량 평가 모드 (Hybrid Retriever 사용)"""
    print(f"--- [EVAL MODE] 하이브리드 전략({args.strategy}) 평가 가동 ---")
    
    # 1. DB 매니저 및 컬렉션 지정
    db_manager = VectorDBManager(api_key=Config.SOLAR_API_KEY, db_path=Config.DB_PATH)
    collection_name = f"meditation_{args.strategy}"
    
    try:
        # 2. 하이브리드 리트리버 연결 (Vector + BM25)
        hybrid_retriever = HybridRetriever(db_manager=db_manager, collection_name=collection_name)
        
        # 3. QA 엔진에 주입
        qa_engine = QAEngine(retriever=hybrid_retriever, api_key=Config.SOLAR_API_KEY)
        
        # 4. LangSmith 평가 실행
        runner = EvaluationRunner(engine=qa_engine)
        runner.run_suite(dataset_name="meditation_qa_v1")
        
    except Exception as e:
        print(f"평가 중 오류가 발생했소. 혹시 Ingest를 먼저 하지 않았소? ({e})")

def run_serve(args):
    """[팀 D] 실서비스 모드 (UI/CLI)"""
    print(f"--- [SERVE MODE] 전우치 명상소 (전략: {args.strategy}) ---")
    
    if args.interface == "web":
        # 비디오 서버 시작 (백그라운드)
        start_video_server()
        
        # Streamlit 웹 화면을 띄우겠소
        print("Streamlit 웹 화면을 띄우겠소...")
        print("브라우저에서 http://localhost:8501 을 열어주시오.")
        print("(Streamlit 서버 종료: Ctrl+C)")
        print()
        
        # subprocess로 실행
        import time
        time.sleep(1)
        subprocess.run([sys.executable, "-m", "streamlit", "run", "src/ui/app.py"])
        return
    else:
        # CLI 모드
        run_serve_cli(args)

def run_serve_cli(args):
    """CLI 모드 (터미널 대화)"""
    db_manager = VectorDBManager(api_key=Config.SOLAR_API_KEY, db_path=Config.DB_PATH)
    collection_name = f"meditation_{args.strategy}"
    
    try:
        # 하이브리드 리트리버 생성
        hybrid_retriever = HybridRetriever(db_manager=db_manager, collection_name=collection_name)
        qa_engine = QAEngine(retriever=hybrid_retriever, api_key=Config.SOLAR_API_KEY)
        
        # Agent (Orchestrator) 연결
        persona = JeonWoochiPersona.SYSTEM_PROMPT
        agent = JeonWoochiAgent(persona=persona, qa_engine=qa_engine)
        
        print(">>> 전우치 도사가 깨어났소. (종료: exit)")
        while True:
            user_input = input("User: ")
            if user_input.lower() in ["exit", "quit"]:
                print("전우치: 인연이 닿으면 또 보세.")
                break
            
            # 에이전트 답변 생성
            response = agent.chat(user_input)
            print(f"전우치: {response}")
            
    except Exception as e:
        print(f"오류: {e}\n먼저 'python main.py ingest'를 실행하여 지식을 채우시오.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="환생한 전우치 명상 RAG 시스템 제어판")
    parser.add_argument("mode", choices=["ingest", "eval", "serve"], help="실행 모드 (적재/평가/서비스)")
    parser.add_argument("--strategy", default="recursive", 
                        choices=["recursive", "semantic", "heading"], 
                        help="청킹 전략 선택 (실험용)")
    parser.add_argument("--interface", default="web", choices=["web", "cli"], help="[Serve 모드용] 인터페이스 선택")
    
    args = parser.parse_args()

    # 모드별 실행
    if args.mode == "ingest":
        run_ingest(args)
    elif args.mode == "eval":
        run_eval(args)
    elif args.mode == "serve":
        run_serve(args)