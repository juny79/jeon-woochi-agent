import streamlit as st
import time
from src.qa.engine import QAEngine
from src.vector_store.manager import VectorDBManager
from src.retriever.hybrid_retriever import HybridRetriever
from src.agent.orchestrator import JeonWoochiAgent
from src.agent.persona_prompt import JeonWoochiPersona
from src.config import Config

# [중요] 에이전트는 무겁기 때문에 캐싱하여 매번 새로 만들지 않게 함
@st.cache_resource
def get_agent(strategy="recursive"):
    # 1. DB 및 리트리버 준비
    db_manager = VectorDBManager(api_key=Config.SOLAR_API_KEY, db_path=Config.DB_PATH)
    collection_name = f"meditation_{strategy}"
    hybrid_retriever = HybridRetriever(db_manager=db_manager, collection_name=collection_name)
    
    # 2. QA 엔진 준비
    qa_engine = QAEngine(retriever=hybrid_retriever, api_key=Config.SOLAR_API_KEY)
    
    # 3. 전우치 에이전트 생성 및 반환
    persona = JeonWoochiPersona.SYSTEM_PROMPT
    return JeonWoochiAgent(persona=persona, qa_engine=qa_engine)

def show_intro():
    """인트로 화면 표시 (전체 화면 영상)"""
    import os
    from pathlib import Path
    
    st.set_page_config(page_title="전우치 명상소", page_icon="🧙‍♂️", layout="wide", initial_sidebar_state="collapsed")
    
    # 사이드바 및 헤더 숨기기
    st.markdown("""
    <style>
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stApp > header {visibility: hidden;}
        .viewerBadge_container {display: none;}
        body, .stApp {margin: 0; padding: 0; background-color: #000;}
        .stVideo {width: 100%; height: 100vh;}
    </style>
    """, unsafe_allow_html=True)
    
    # 비디오 파일 읽기
    video_path = "videos/intro.mp4"
    if os.path.exists(video_path):
        # 절대 경로 얻기
        abs_video_path = os.path.abspath(video_path)
        
        # HTML5 비디오 플레이어 (파일 경로 직접 사용)
        st.markdown(f"""
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 999; background: black;">
            <video id="introVid" 
                   style="width: 100%; height: 100%; object-fit: cover;" 
                   autoplay muted
                   onloadedmetadata="this.muted = false; this.volume = 1.0;">
                <source src="file:///{abs_video_path.replace(chr(92), '/')}" type="video/mp4">
            </video>
        </div>
        <script>
            console.log('Video setup started');
            var vid = document.getElementById('introVid');
            
            if (vid) {{
                // 1.5초 후 언뮤트
                setTimeout(function() {{
                    vid.muted = false;
                    vid.volume = 1.0;
                    console.log('Video unmuted, volume:', vid.volume);
                }}, 1500);
                
                // 메타데이터 로드 시 언뮤트
                vid.addEventListener('loadedmetadata', function() {{
                    console.log('Metadata loaded');
                    vid.muted = false;
                    vid.volume = 1.0;
                }});
                
                // 재생 중일 때도 언뮤트
                vid.addEventListener('play', function() {{
                    console.log('Video playing');
                    vid.muted = false;
                    vid.volume = 1.0;
                }});
            }}
        </script>
        """, unsafe_allow_html=True)
    else:
        st.error(f"영상 파일을 찾을 수 없습니다: {video_path}")
        return
    
    # 8초 카운트다운
    for i in range(8):
        time.sleep(1)
    
    # 세션 상태 업데이트
    st.session_state.show_intro = False
    st.rerun()

def main():
    st.set_page_config(page_title="전우치 명상소", page_icon="🧙‍♂️", layout="wide")
    
    # URL 파라미터에서 strategy 가져오기 (기본값: recursive)
    import sys
    strategy = "recursive"
    if len(sys.argv) > 1:
        # streamlit run app.py -- --strategy semantic 형태로 실행됨
        for i, arg in enumerate(sys.argv):
            if arg == "--strategy" and i + 1 < len(sys.argv):
                strategy = sys.argv[i + 1]
    
    st.title("🧙‍♂️ 환생한 전우치의 명상소")
    st.caption(f"하이브리드 검색 기반 에이전트 가동 중 (전략: {strategy})")

    # 사이드바: 정보
    with st.sidebar:
        st.header("✨ 전우치 도사의 명상소")
        st.info("전우치의 명상 비급을 배워보세요.")
        st.markdown("---")
        st.markdown("""
        **기능:**
        - 명상 방법 안내
        - 스트레스 해소법
        - 호흡 기술
        """)

    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 이전 대화 출력
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력 처리
    if prompt := st.chat_input("전우치 도사께 질문하세요..."):
        # 유저 메시지 표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 에이전트 답변 생성
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🤔 전우치가 생각 중이오...")
            
            try:
                # 에이전트 실행
                agent = get_agent(strategy)
                response = agent.chat(prompt)
                
                message_placeholder.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                message_placeholder.error(f"도술에 실패했소: {e}")

if __name__ == "__main__":
    # 첫 방문 여부 확인
    if "show_intro" not in st.session_state:
        st.session_state.show_intro = True
    
    # 인트로 표시 또는 메인 페이지 표시
    if st.session_state.show_intro:
        show_intro()
    else:
        main()