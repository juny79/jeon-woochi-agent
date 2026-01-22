import streamlit as st
import time
import os
import base64
from pathlib import Path
from src.qa.engine import QAEngine
from src.vector_store.manager import VectorDBManager
from src.retriever.hybrid_retriever import HybridRetriever
from src.agent.orchestrator import JeonWoochiAgent
from src.agent.persona_prompt import JeonWoochiPersona
from src.config import Config

# 반드시 다른 모든 Streamlit 명령보다 먼저 실행되어야 합니다
st.set_page_config(page_title="전우치 명상소", page_icon="🧙‍♂️", layout="wide")

# [전역 테마 설정] 제미나이 프리미엄 다크
st.markdown("""
<style>
    /* 전체 배경색 통일 */
    html, body, .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stApp"], 
    [data-testid="stBottom"],
    [data-testid="stHeader"],
    header, footer {
        background-color: #131314 !important;
        color: #ffffff !important;
    }
    
    /* 하단 화이트 바 원천 차단 */
    [data-testid="stBottomBlockContainer"] {
        background-color: transparent !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

def load_image_as_base64(filename):
    """이미지를 base64로 인코딩하여 반환"""
    filepath = ASSETS_DIR / filename
    if filepath.exists():
        with open(filepath, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

# 전우치 캐릭터 SVG (이미지가 없을 경우를 대비한 대체제)
JEON_WOOCHI_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 240">
  <defs>
    <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#e0a87e;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#d4956b;stop-opacity:1" />
    </linearGradient>
    <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="0" dy="8" stdDeviation="4" flood-opacity="0.3" />
    </filter>
  </defs>
  
  <!-- 모자 -->
  <path d="M 60 50 Q 100 20 140 50 L 135 60 Q 100 35 65 60 Z" fill="#1a1a1a" filter="url(#shadow)"/>
  <circle cx="100" cy="40" r="8" fill="#333"/>
  
  <!-- 얼굴 -->
  <circle cx="100" cy="90" r="35" fill="url(#bodyGrad)" filter="url(#shadow)"/>
  
  <!-- 눈 -->
  <circle cx="85" cy="80" r="5" fill="#333"/>
  <circle cx="115" cy="80" r="5" fill="#333"/>
  <circle cx="87" cy="78" r="2" fill="#fff"/>
  <circle cx="117" cy="78" r="2" fill="#fff"/>
  
  <!-- 입 -->
  <path d="M 85 100 Q 100 110 115 100" stroke="#c0673f" stroke-width="2" fill="none" stroke-linecap="round"/>
  
  <!-- 몸(도포) -->
  <path d="M 70 115 L 65 190 Q 100 200 135 190 L 130 115" fill="#4a5568" filter="url(#shadow)"/>
  
  <!-- 빨간 스카프 -->
  <path d="M 75 120 Q 100 135 125 120 L 128 125 Q 100 140 72 125 Z" fill="#d32f2f"/>
  
  <!-- 지팡이 -->
  <rect x="135" y="110" width="4" height="60" fill="#8b7355" filter="url(#shadow)" transform="rotate(25 137 140)"/>
  <circle cx="142" cy="108" r="8" fill="#c9b495" filter="url(#shadow)" transform="rotate(25 137 140)"/>
</svg>
"""

# 에이전트는 무겁기 때문에 캐싱하여 매번 새로 만들지 않게 함
@st.cache_resource
def get_agent(strategy="recursive"):
    db_manager = VectorDBManager(api_key=Config.SOLAR_API_KEY, db_path=Config.DB_PATH)
    collection_name = f"meditation_{strategy}"
    hybrid_retriever = HybridRetriever(db_manager=db_manager, collection_name=collection_name)
    
    qa_engine = QAEngine(retriever=hybrid_retriever, api_key=Config.SOLAR_API_KEY)
    
    persona = JeonWoochiPersona.SYSTEM_PROMPT
    return JeonWoochiAgent(persona=persona, qa_engine=qa_engine)

def show_intro():
    """인트로 화면 (시네마틱 감성 강조)"""
    
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@200;400;700&display=swap');

        [data-testid="collapsedControl"], #MainMenu, footer, header {
            visibility: hidden !important;
            display: none !important;
        }
        
        .stApp {
            background-color: #131314 !important;
        }

        /* 배경 비디오 설정 */
        .video-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: -100;
            overflow: hidden;
            background-color: #131314;
        }

        .video-background {
            width: 100%;
            height: 100%;
            object-fit: cover;
            opacity: 0.45;
            filter: saturate(0.8) contrast(1.1);
        }

        .video-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, transparent 20%, rgba(0,0,0,0.8) 100%);
            z-index: -99;
        }

        /* 메인 텍스트 영역 */
        .intro-content {
            position: fixed;
            top: 45%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            width: 100%;
            z-index: 10;
        }

        .intro-top-label {
            font-size: 0.8rem;
            color: rgba(255,255,255,0.5);
            letter-spacing: 0.5rem;
            text-transform: uppercase;
            margin-bottom: 1.5rem;
            animation: fadeInDown 1.5s ease-out;
        }

        .intro-title {
            font-family: 'Noto Serif KR', serif !important;
            font-size: 5.5rem;
            font-weight: 700;
            background: linear-gradient(to bottom, #ffffff 40%, #a0a0a0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            letter-spacing: -1px;
            animation: fadeInUp 1.2s ease-out, textShimmer 3s ease-in-out infinite;
        }

        .intro-divider {
            width: 60px;
            height: 1px;
            background: rgba(255,255,255,0.3);
            margin: 2.5rem auto;
            animation: expand 2.5s ease-in-out forwards;
        }

        .intro-subtitle {
            font-size: 1.2rem;
            color: rgba(255,255,255,0.6);
            font-weight: 300;
            letter-spacing: 0.3rem;
            animation: fadeInUp 1.8s ease-out, pulseText 4s ease-in-out infinite;
        }

        /* 애니메이션 효과 */
        @keyframes textShimmer {
            0%, 100% { filter: brightness(1) blur(0px); }
            50% { filter: brightness(1.4) blur(0.5px) drop-shadow(0 0 15px rgba(255,255,255,0.4)); }
        }

        @keyframes pulseText {
            0%, 100% { opacity: 0.5; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.01); }
        }

        /* 프리미엄 글래스 버튼 */
        .stButton > button {
            position: fixed !important;
            top: 75% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            background: rgba(255, 255, 255, 0.05) !important;
            color: white !important;
            font-size: 1rem !important;
            padding: 1rem 3rem !important;
            border-radius: 4px !important; 
            font-weight: 400 !important;
            border: 1px solid rgba(255,255,255,0.3) !important;
            backdrop-filter: blur(20px) !important;
            transition: all 0.5s ease !important;
            z-index: 9999 !important;
            letter-spacing: 0.2rem !important;
            text-transform: uppercase !important;
            width: auto !important;
        }

        .stButton > button:hover {
            background: white !important;
            color: black !important;
            border-color: white !important;
            box-shadow: 0 0 30px rgba(255,255,255,0.2) !important;
            transform: translate(-50%, -55%) !important;
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes expand {
            from { width: 0; }
            to { width: 80px; }
        }
    </style>
    
    <div class="video-container">
        <video autoplay muted loop playsinline class="video-background">
            <source src="http://127.0.0.1:8889/videos/intro.mp4" type="video/mp4">
        </video>
        <div class="video-overlay"></div>
    </div>

    <div class="intro-content">
        <div class="intro-top-label">The Meditation Master</div>
        <h1 class="intro-title">전우치 명상소</h1>
        <div class="intro-divider"></div>
        <p class="intro-subtitle">마음의 평온을 찾는 여정</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("ENTER THE JOURNEY", key="start_app_btn"):
        st.markdown("""
            <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background-color:#131314; z-index:100001;"></div>
        """, unsafe_allow_html=True)
        time.sleep(0.3)
        st.session_state.show_intro = False
        st.rerun()

def main():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700&display=swap');

        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp_"], .stApp, [data-testid="stBottom"] {
            background-color: #131314 !important;
            color: #e3e3e3 !important;
        }

        [data-testid="stBottomBlockContainer"] {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        [data-testid="stMainBlockContainer"] {
            max-width: 900px !important;
            padding: 4rem 2rem 10rem 2rem !important;
            margin: 0 auto !important;
            background-color: transparent !important;
        }

        [data-testid="stSidebar"] {
            background-color: #1e1f20 !important;
            border-right: 1px solid #333 !important;
        }
        
        [data-testid="stSidebarContent"] * {
            color: #e3e3e3 !important;
        }

        /* 사이드바 제미나이 스타일링 */
        [data-testid="stSidebar"] {
            background-color: #1e1f20 !important;
            border-right: 1px solid #333 !important;
        }

        [data-testid="stSidebarNav"] {
            background-color: transparent !important;
        }

        .sidebar-new-chat {
            background-color: #333537 !important;
            color: #e3e3e3 !important;
            border-radius: 20px !important;
            padding: 10px 20px !important;
            text-align: center !important;
            cursor: pointer !important;
            margin-bottom: 20px !important;
            font-size: 0.9rem !important;
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
            border: 1px solid #444 !important;
        }

        .sidebar-section-label {
            color: #9aa0a6 !important;
            font-size: 0.8rem !important;
            margin: 20px 0 10px 10px !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }

        header, footer { background-color: transparent !important; }

        .welcome-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            margin-top: 15vh;
            width: 100%;
        }

        .welcome-title {
            font-size: 3.5rem !important;
            font-weight: 500 !important;
            background: linear-gradient(74deg, #4285f4 0, #9b72cb 9%, #d96570 20%, #e3e3e3 40%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.1rem !important;
        }

        .welcome-subtitle {
            font-size: 3.5rem !important;
            font-weight: 500 !important;
            color: #444746 !important;
            margin-top: 0 !important;
            margin-bottom: 3rem !important;
        }

        /* 제미나이 스타일 질문창 (가운데 정렬 + 다크 캡슐) */
        div[data-testid="stChatInput"] {
            position: fixed !important;
            bottom: 40px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: 800px !important;
            max-width: 90% !important;
            background-color: #1e1f20 !important;
            border-radius: 28px !important;
            border: none !important;
            padding: 4px 12px !important;
            z-index: 10000 !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        }

        div[data-testid="stChatInput"] textarea {
            background-color: transparent !important;
            color: #e3e3e3 !important; 
            caret-color: #ffffff !important;
            font-size: 1rem !important;
            line-height: 1.5 !important;
            -webkit-text-fill-color: #e3e3e3 !important;
            padding-top: 10px !important;
        }

        div[data-testid="stChatInput"] button {
            background-color: transparent !important;
            color: #e3e3e3 !important;
        }

        [data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
            background-color: transparent !important;
            border: none !important;
        }

        div[data-testid="stChatInput"]:focus-within {
            border-color: #8ab4f8 !important;
        }

        [data-testid="stChatInputContainer"] {
            background-color: transparent !important;
        }

        /* 캐릭터 떠다니는 애니메이션 */
        .jeon-woochi-container {
            position: fixed;
            left: 30px;
            bottom: 30px;
            width: 170px;
            z-index: 10000 !important;
            pointer-events: none;
            display: block !important;
            visibility: visible !important;
        }

        .jeon-woochi-float {
            width: 100%;
            filter: drop-shadow(0 0 25px rgba(138, 180, 248, 0.2));
            animation: floatAnim 4s ease-in-out infinite;
        }

        @keyframes floatAnim {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-20px); }
        }

        .jeon-woochi-bg {
            position: fixed;
            right: -5%;
            bottom: -5%;
            width: 35vw;
            max-width: 700px;
            z-index: -1;
            opacity: 0.05;
            filter: blur(1px);
            pointer-events: none;
            display: block !important;
        }

        /* 애니메이션 효과: 씽킹 빔 */
        .thinking-beam {
            width: 100%;
            height: 4px;
            background: rgba(255,255,255,0.05);
            border-radius: 2px;
            overflow: hidden;
            margin-bottom: 2rem;
        }

        .thinking-beam-inner {
            width: 30%;
            height: 100%;
            background: linear-gradient(90deg, transparent, #8ab4f8, transparent);
            animation: beamMove 1.5s infinite;
        }

        @keyframes beamMove {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(330%); }
        }

        /* 액션 버튼 스타일 */
        .stButton > button:not([key="start_app_btn"]):not([key="new_chat_btn"]) {
            background-color: #1e1f20 !important;
            color: #e3e3e3 !important;
            border: 1px solid #333 !important;
            border-radius: 16px !important;
            height: 140px !important;
            padding: 1.5rem !important;
            text-align: left !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: space-between !important;
        }

        .stButton > button:hover:not([key="start_app_btn"]):not([key="new_chat_btn"]) {
            background-color: #2a2b2e !important;
            border-color: #444 !important;
            transform: translateY(-5px);
        }

        .stChatMessage {
            background-color: transparent !important;
            padding: 1.5rem 0 !important;
        }

        /* 채팅 결과물 글자 가시성 강화 (모든 요소 포함) */
        .stChatMessage [data-testid="stMarkdownContainer"],
        .stChatMessage [data-testid="stMarkdownContainer"] p,
        .stChatMessage [data-testid="stMarkdownContainer"] li,
        .stChatMessage [data-testid="stMarkdownContainer"] span,
        .stChatMessage [data-testid="stMarkdownContainer"] div {
            color: #ffffff !important;
            font-size: 1.1rem !important;
            line-height: 1.7 !important;
        }

        .stChatMessage [data-testid="stMarkdownContainer"] h1,
        .stChatMessage [data-testid="stMarkdownContainer"] h2,
        .stChatMessage [data-testid="stMarkdownContainer"] h3,
        .stChatMessage [data-testid="stMarkdownContainer"] h4,
        .stChatMessage [data-testid="stMarkdownContainer"] h5,
        .stChatMessage [data-testid="stMarkdownContainer"] strong {
            color: #ffffff !important;
            font-weight: 700 !important;
        }
        
        [data-testid="stChatMessageAvatar"] {
            background-color: #333 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    jeon_woochi_b_b64 = load_image_as_base64("jeon-woochi_b.png")
    if jeon_woochi_b_b64:
        st.markdown(f"""
        <div class="jeon-woochi-container">
            <div class="jeon-woochi-float">
                <img src="data:image/png;base64,{jeon_woochi_b_b64}" style="width: 100%;">
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="jeon-woochi-container">
            <div class="jeon-woochi-float">
                {JEON_WOOCHI_SVG}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    jeon_woochi_c_b64 = load_image_as_base64("jeon-woochi_c.png")
    if jeon_woochi_c_b64:
        st.markdown(f"""
        <img src="data:image/png;base64,{jeon_woochi_c_b64}" class="jeon-woochi-bg" alt="배경">
        """, unsafe_allow_html=True)
    
    import sys
    strategy = "recursive"
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--strategy" and i + 1 < len(sys.argv):
                strategy = sys.argv[i + 1]
    
    with st.sidebar:
        st.markdown("""
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 25px;">
                <span style="font-size: 1.5rem;">🧙‍♂️</span>
                <span style="font-size: 1.2rem; font-weight: 500; color: white;">전우치 명상소</span>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("➕ 새 채팅", use_container_width=True, key="new_chat_btn"):
            st.session_state.messages = []
            st.session_state.show_welcome = True
            st.rerun()
            
        st.markdown('<div class="sidebar-section-label">최근 항목</div>', unsafe_allow_html=True)
        st.caption("내역이 없습니다.")
        
        st.markdown('<div class="sidebar-section-label">설정</div>', unsafe_allow_html=True)
        strategy = st.selectbox("명상 방식", ("recursive", "semantic", "heading"), 
                                 index=("recursive", "semantic", "heading").index(strategy),
                                 label_visibility="collapsed")
        
        st.divider()
        st.markdown("""
            <div style="margin-top: auto; padding-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 12px; color: #9aa0a6; cursor: pointer; padding: 8px;">
                    <span>🕒</span> <span>활동</span>
                </div>
                <div style="display: flex; align-items: center; gap: 12px; color: #9aa0a6; cursor: pointer; padding: 8px;">
                    <span>⚙️</span> <span>설정 및 도움말</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True

    st.markdown('<div class="main-content">', unsafe_allow_html=True)
  
    if st.session_state.show_welcome and len(st.session_state.messages) == 0:
        st.markdown("""
        <div class="welcome-container">
            <h1 class="welcome-title">✨ 준영님, 안녕하세요</h1>
            <h1 class="welcome-subtitle">무엇을 도와드릴까요?</h1>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div style="max-width: 820px; margin: 0 auto;">', unsafe_allow_html=True)
        
        cols = st.columns(4)
        actions = [
            {"icon": "🧘", "label": "명상 시작", "desc": "가이드 명상을 시작합니다."},
            {"icon": "📝", "label": "고민 상담", "desc": "지친 마음에 위로를 건넵니다."},
            {"icon": "📖", "label": "지혜 찾기", "desc": "고전의 가르침을 전해드립니다."},
            {"icon": "✨", "label": "무드 명상", "desc": "오늘의 기분에 맞춰 추천합니다."}
        ]
        for i, act in enumerate(actions):
            with cols[i]:
                if st.button(f"{act['icon']}\n\n**{act['label']}**\n{act['desc']}", key=f"action_{i}"):
                    st.session_state.messages.append({"role": "user", "content": act["label"]})
                    st.session_state.show_welcome = False
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
  
    else:
      st.markdown('<div style="max-width: 820px; margin: 0 auto;">', unsafe_allow_html=True)
      st.markdown('<div class="messages-section">', unsafe_allow_html=True)
      jeon_woochi_b_b64 = load_image_as_base64("jeon-woochi_b.png")
      
      for message in st.session_state.messages:
          avatar_img = f"data:image/png;base64,{jeon_woochi_b_b64}" if message["role"] == "assistant" and jeon_woochi_b_b64 else None
          with st.chat_message(message["role"], avatar=avatar_img):
              st.markdown(message["content"])
      st.markdown('</div>', unsafe_allow_html=True)
      st.markdown('</div>', unsafe_allow_html=True)
  
    prompt = st.chat_input("전우치에게 고민을 털어놓으세요...")
  
    if prompt:
      st.session_state.show_welcome = False
      st.session_state.messages.append({"role": "user", "content": prompt})
      st.rerun()

    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
      user_msg = st.session_state.messages[-1]["content"]
      
      jeon_woochi_b_b64 = load_image_as_base64("jeon-woochi_b.png")
      avatar_img = f"data:image/png;base64,{jeon_woochi_b_b64}" if jeon_woochi_b_b64 else None
      
      with st.chat_message("assistant", avatar=avatar_img):
          status_placeholder = st.empty()
          with status_placeholder.container():
              st.markdown("""
              <div style="color: #8ab4f8; font-size: 0.9rem; margin-bottom: 0.5rem;">
                  전우치가 생각에 잠겼습니다...
              </div>
              <div class="thinking-beam">
                  <div class="thinking-beam-inner"></div>
              </div>
              """, unsafe_allow_html=True)
          
          try:
              agent = get_agent(strategy)
              response = agent.chat(user_msg)
              
              status_placeholder.empty()
              st.markdown(response)
              st.session_state.messages.append({"role": "assistant", "content": response})
          except Exception as e:
              status_placeholder.error(f"❌ 오류 발생: {e}")
  
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    if "show_intro" not in st.session_state:
        st.session_state.show_intro = True
    if st.session_state.show_intro:
        show_intro()
    else:
        main()
