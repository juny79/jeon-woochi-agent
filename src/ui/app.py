import streamlit as st
import time
import os
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
    """인트로 화면 표시 (전체 화면 영상 + 자동재생 + 음성)"""
    
    # 사이드바 및 헤더 숨기기
    st.markdown("""
    <style>
        /* 전체 화면 설정 */
        html, body {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            height: 100% !important;
            background: #000 !important;
        }
        
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        #MainMenu {
            visibility: hidden !important;
        }
        footer {
            visibility: hidden !important;
        }
        .stApp > header {
            visibility: hidden !important;
        }
        .viewerBadge_container {
            display: none !important;
        }
        
        /* Streamlit 컨테이너 전체 화면 */
        .stAppViewContainer {
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            height: 100vh !important;
        }
        
        .stApp {
            margin: 0 !important;
            padding: 0 !important;
            background: #000 !important;
        }
        
        /* 비디오 컨테이너 */
        #intro-video-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            z-index: 9999;
            background: #000;
        }
        
        #intro-video-container video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        
        #countdown {
            position: absolute;
            bottom: 20px;
            right: 20px;
            color: white;
            font-size: 32px;
            font-weight: bold;
            z-index: 10000;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 비디오 파일 확인
    video_path = "videos/intro.mp4"
    if os.path.exists(video_path):
        # HTTP 서버에서 스트리밍 (파일 서버 포트 8889)
        st.markdown(f"""
        <div id="intro-video-container">
            <video id="intro-video"
                   autoplay
                   playsinline
                   style="width: 100%; height: 100%; object-fit: cover;">
                <source src="http://127.0.0.1:8889/videos/intro.mp4" type="video/mp4">
                <source src="/videos/intro.mp4" type="video/mp4">
            </video>
            <div id="countdown">8</div>
        </div>
        
        <script>
            console.log('[INTRO] 인트로 스크립트 시작');
            
            // 비디오 요소
            var video = document.getElementById('intro-video');
            var countdown = document.getElementById('countdown');
            
            console.log('[INTRO] 비디오 요소 찾음:', video ? 'YES' : 'NO');
            
            if (video) {{
                // 비디오 로드 에러 핸들러
                video.addEventListener('error', function(e) {{
                    console.error('[INTRO] 비디오 로드 에러:', e.message);
                    console.error('[INTRO] 에러 상세:', video.error);
                }});
                
                // 비디오 로드 시작
                video.addEventListener('loadstart', function() {{
                    console.log('[INTRO] 비디오 로드 시작');
                }});
                
                // canplay 이벤트
                video.addEventListener('canplay', function() {{
                    console.log('[INTRO] 비디오 재생 가능');
                }});
                
                // 자동 재생 시도
                console.log('[INTRO] 자동 재생 시도...');
                var playPromise = video.play();
                if (playPromise !== undefined) {{
                    playPromise.then(function() {{
                        console.log('[INTRO] 비디오 재생 시작');
                        video.muted = false;
                        video.volume = 1.0;
                        console.log('[INTRO] 음성 활성화: muted=false, volume=1.0');
                    }}).catch(function(error) {{
                        console.error('[INTRO] 자동 재생 실패:', error.name, error.message);
                    }});
                }}
                
                // 메타데이터 로드 시
                video.addEventListener('loadedmetadata', function() {{
                    console.log('[INTRO] 메타데이터 로드됨, 재생 길이: ' + video.duration + '초');
                    video.muted = false;
                    video.volume = 1.0;
                }});
                
                // 재생 이벤트
                video.addEventListener('play', function() {{
                    console.log('[INTRO] 재생 중');
                }});
                
                // 일시정지 이벤트
                video.addEventListener('pause', function() {{
                    console.log('[INTRO] 일시정지됨');
                }});
                
                // 음량 명시적 설정
                video.volume = 1.0;
                video.muted = false;
                console.log('[INTRO] 초기 음량 설정: volume=1.0, muted=false');
            }} else {{
                console.error('[INTRO] 비디오 요소를 찾을 수 없습니다');
            }}
            
            // 카운트다운 (8초)
            console.log('[INTRO] 카운트다운 시작');
            var count = 8;
            var interval = setInterval(function() {{
                count--;
                if (countdown) {{
                    countdown.textContent = count;
                }}
                if (count <= 0) {{
                    clearInterval(interval);
                    console.log('[INTRO] 카운트다운 완료');
                }}
            }}, 1000);
        </script>
        """, unsafe_allow_html=True)
        
    else:
        st.error(f"영상 파일을 찾을 수 없습니다: {video_path}")
        return
    
    # 8초 카운트다운
    time.sleep(8)
    
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