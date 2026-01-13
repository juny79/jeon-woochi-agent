import os
import argparse
import sys
import subprocess
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

def run_ingest(args):
    """[팀 A & B] 데이터 적재 모드 (Markdown + News -> Chunk -> Hybrid Indexing)"""
    print(f"--- [INGEST MODE] 전략: {args.strategy} / 하이브리드 적재 시작 ---")
    
    all_docs = []

    # 1. 로컬 마크다운 지식 로드 (우선순위 높음)
    md_docs = load_markdown_knowledge("data/knowledge.md")
    all_docs.extend(md_docs)

    # 2. (선택사항) 뉴스 크롤러 실행
    # 실제 운영 시에는 크롤링도 함께 수행하여 지식을 확장할 수 있소.
    # crawler = MeditationNewsCrawler()
    # news_docs = crawler.fetch_data(query="명상과 뇌과학")
    # all_docs.extend(news_docs)
    
    if not all_docs:
        print("적재할 지식이 하나도 없구려. 경로를 확인하시오.")
        return

    # 3. 청킹 전략 적용 (Factory)
    chunker = ChunkerFactory.get_chunker(args.strategy)
    # LangChain Document 객체 리스트로 변환 및 분할
    chunks = chunker.split_documents(all_docs)
    print(f"총 {len(chunks)}개의 지식 조각으로 나누었소.")
    
    # 4. 저장 (Vector DB + BM25 인덱스 동시 생성)
    # VectorDBManager.add_documents 내부에서 pickle로 BM25도 저장하도록 수정되었음
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
        # Streamlit 직접 실행 (subprocess로 streamlit run 명령 실행)
        print("Streamlit 웹 화면을 띄우겠소...")
        print("브라우저에서 http://localhost:8501 을 열어주시오.")
        print("(Streamlit 서버 종료: Ctrl+C)")
        
        # 환경변수 설정
        env = os.environ.copy()
        env["STREAMLIT_SERVER_HEADLESS"] = "false"
        
        # streamlit run src/ui/app.py 실행
        try:
            subprocess.run(
                ["streamlit", "run", "src/ui/app.py", "--", "--strategy", args.strategy],
                env=env
            )
        except Exception as e:
            print(f"Streamlit 실행 오류: {e}")
            print("대신 CLI 모드로 전환합니다...")
            run_serve_cli(args)
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