import streamlit as st
import streamlit.components.v1 as components
import time
import os
import base64
from pathlib import Path
from datetime import datetime
from src.qa.engine import QAEngine
from src.vector_store.manager import VectorDBManager
from src.retriever.hybrid_retriever import HybridRetriever
from src.agent.orchestrator import JeonWoochiAgent
from src.agent.persona_prompt import JeonWoochiPersona
from src.config import Config
from src.db.base import SessionLocal, engine, Base
from src.db.models import ChatSession, ChatMessage

# ── DB 초기화 (테이블이 없으면 생성) ──────────────────────────
Base.metadata.create_all(bind=engine)

# SQLite 마이그레이션: is_pinned 컬럼이 없으면 추가
try:
    from sqlalchemy import inspect as _sa_inspect, text as _sa_text
    with engine.connect() as _conn:
        _cols = [c["name"] for c in _sa_inspect(engine).get_columns("chat_sessions")]
        if "is_pinned" not in _cols:
            _conn.execute(_sa_text(
                "ALTER TABLE chat_sessions ADD COLUMN is_pinned BOOLEAN DEFAULT 0"
            ))
            _conn.commit()
except Exception:
    pass

# ── DB 헬퍼 함수들 ────────────────────────────────────────────
def db_create_session(first_user_msg: str) -> int:
    """새 ChatSession 레코드를 만들고 id 반환"""
    title = first_user_msg[:40] + ("…" if len(first_user_msg) > 40 else "")
    db = SessionLocal()
    try:
        session = ChatSession(title=title)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id
    finally:
        db.close()

def db_add_message(session_id: int, role: str, content: str):
    """특정 세션에 메시지 한 건 추가"""
    db = SessionLocal()
    try:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        db.add(msg)
        db.commit()
    finally:
        db.close()

def db_get_sessions(limit: int = 30):
    """최신순 세션 목록 반환. 고정된 항목이 맨 위. (id, title, is_pinned, created_at)"""
    db = SessionLocal()
    try:
        rows = (db.query(ChatSession)
                  .order_by(ChatSession.is_pinned.desc(),
                            ChatSession.created_at.desc())
                  .limit(limit)
                  .all())
        return [(r.id, r.title, bool(r.is_pinned), r.created_at) for r in rows]
    finally:
        db.close()

def db_load_messages(session_id: int):
    """세션의 메시지 목록 반환 [ {"role": ..., "content": ...}, ... ]"""
    db = SessionLocal()
    try:
        rows = (db.query(ChatMessage)
                  .filter(ChatMessage.session_id == session_id)
                  .order_by(ChatMessage.created_at)
                  .all())
        return [{"role": r.role, "content": r.content} for r in rows]
    finally:
        db.close()

def db_delete_session(session_id: int):
    """세션 및 하위 메시지 전체 삭제 (cascade)"""
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            db.delete(session)
            db.commit()
    finally:
        db.close()

def db_rename_session(session_id: int, new_title: str):
    """세션 제목 변경"""
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.title = new_title[:60]
            db.commit()
    finally:
        db.close()

def db_pin_session(session_id: int, pinned: bool):
    """세션 고정/고정 해제"""
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.is_pinned = pinned
            db.commit()
    finally:
        db.close()

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
    [data-testid="stBottom"] > div,
    [data-testid="stBottom"] > section,
    [data-testid="stBottomBlockContainer"],
    [data-testid="stBottomBlockContainer"] > div,
    header, footer {
        background-color: #131314 !important;
        color: #ffffff !important;
        color-scheme: dark !important;
    }

    /* 브라우저 기본 input/textarea 흰 배경 전역 차단 */
    input, textarea, select {
        color-scheme: dark !important;
        background-color: transparent !important;
        color: #f0f0f0 !important;
    }
    
    /* 하단 화이트 바 원천 차단 */
    [data-testid="stBottomBlockContainer"] {
        background-color: #131314 !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* 모든 Streamlit 컨테이너 배경 강제 다크 */
    [data-testid="stVerticalBlock"],
    [data-testid="stHorizontalBlock"],
    [data-testid="stElementContainer"],
    [data-testid="stLayoutWrapper"],
    .element-container,
    [class*="block-container"],
    [class*="stBlock"],
    section[data-testid="stSidebar"] ~ div {
        background-color: transparent !important;
    }

    /* 스트리밍 출력 요소 */
    [data-testid="stText"],
    [data-testid="stText"] p,
    [data-testid="stText"] span {
        color: #e3e3e3 !important;
        -webkit-text-fill-color: #e3e3e3 !important;
        background-color: transparent !important;
    }

    /* Streamlit 기본 텍스트 color 재정의 */
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown span {
        color: #e3e3e3 !important;
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
            max-width: 860px !important;
            padding: 4rem 2rem 10rem 2rem !important;
            margin: 0 auto !important;
            background-color: transparent !important;
        }

        /* ════ 사이드바 — 전체 wildcard reset ════ */
        [data-testid="stSidebar"] {
            background-color: #1e1f20 !important;
            border-right:     1px solid #2a2b2e !important;
        }
        /* selector 이름 몰라도 되는 방식: 사이드바 모든 요소 여백 0 */
        [data-testid="stSidebar"] * {
            margin:           0 !important;
            padding:          0 !important;
            gap:              0 !important;
            min-height:       0 !important;
            border:           none !important;
            box-shadow:       none !important;
            background-color: transparent !important;
            background:       transparent !important;
        }
        /* 버튼 자체는 padding 복원 */
        [data-testid="stSidebar"] button {
            padding: 6px 12px !important;
        }
        /* 사이드바 전체 레이아웃 padding 복원 */
        [data-testid="stSidebarContent"] {
            padding:   8px !important;
            gap:       0   !important;
        }
        [data-testid="stSidebarContent"] * { color: #e3e3e3 !important; }

        /* ── 헤더 ── */
        .sb-header {
            display:     flex;
            align-items: center;
            gap:         10px;
            padding:     8px 6px 14px;
            font-size:   0.95rem;
            font-weight: 600;
            flex-shrink: 0;
        }
        .sb-logo {
            width:           30px;
            height:          30px;
            background:      linear-gradient(135deg, #7c3aed 0%, #4338ca 100%);
            border-radius:   8px;
            display:         inline-flex;
            align-items:     center;
            justify-content: center;
            font-size:       17px;
            line-height:     1;
            flex-shrink:     0;
        }

        /* ── 섹션 타이틀 ── */
        .sb-section-title {
            font-size:      0.72rem;
            color:          #5f6368 !important;
            -webkit-text-fill-color: #5f6368 !important;
            letter-spacing: 0.3px;
            padding:        12px 14px 4px;
            flex-shrink:    0;
        }
        .sb-empty {
            font-size:  0.78rem;
            color:      #5f6368 !important;
            padding:    3px 4px;
            font-style: italic;
        }

        /* ── 새 채팅 버튼 (primary) — Gemini flat pill ── */
        [data-testid="stSidebar"] button[data-testid="baseButton-primary"] {
            background-color: transparent !important;
            color:            #e3e3e3 !important;
            border:           1px solid rgba(255,255,255,0.12) !important;
            border-radius:    24px !important;
            font-size:        0.88rem !important;
            padding:          8px 18px !important;
            height:           36px !important;
            margin:           0 !important;
            width:            auto !important;
            text-align:       left !important;
            font-weight:      400 !important;
            display:          inline-flex !important;
            align-items:      center !important;
            box-shadow:       none !important;
        }
        [data-testid="stSidebar"] button[data-testid="baseButton-primary"]:hover {
            background-color: rgba(255,255,255,0.08) !important;
        }

        /* ── 세션 타이틀 버튼 — Gemini flat row ── */
        [data-testid="stSidebar"] button[data-testid="baseButton-secondary"] {
            background-color: transparent !important;
            color:            #c4c7c5 !important;
            border:           none !important;
            border-radius:    20px !important;
            font-size:        0.85rem !important;
            padding:          6px 12px !important;
            min-height:       36px !important;
            height:           36px !important;
            line-height:      1.3 !important;
            text-align:       left !important;
            white-space:      nowrap !important;
            overflow:         hidden !important;
            text-overflow:    ellipsis !important;
            width:            100% !important;
            font-weight:      400 !important;
            display:          block !important;
            box-shadow:       none !important;
        }
        [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover {
            background-color: rgba(255,255,255,0.08) !important;
            color:            #e3e3e3 !important;
        }

        /* ── ⋮ 메뉴 버튼 — 작고 미묘하게, hover시 강조 ── */
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:last-child div.stButton > button {
            color:         #5f6368 !important;
            min-height:    34px !important;
            height:        34px !important;
            padding:       4px 6px !important;
            font-size:     1rem !important;
            border-radius: 50% !important;
        }
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:hover [data-testid="stColumn"]:last-child div.stButton > button {
            color: #9aa0a6 !important;
        }
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"]:last-child div.stButton > button:hover {
            background-color: rgba(255,255,255,0.1) !important;
            color:            #e3e3e3 !important;
        }

        /* ── 컨텍스트 메뉴 구분선 ── */
        .sb-ctx-divider {
            height:     1px;
            background: rgba(255,255,255,0.08);
            margin:     2px 0;
        }

        /* ── 스페이서 ── */
        .sb-spacer { flex: 1; min-height: 8px; }

        /* ── 설정 expander — 무테두리 flat ── */
        [data-testid="stSidebar"] [data-testid="stExpander"] {
            background-color: transparent !important;
            border:           none !important;
            border-radius:    8px !important;
            margin-bottom:    0 !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] summary {
            color:         #9aa0a6 !important;
            font-size:     0.84rem !important;
            padding:       8px 8px !important;
            border-radius: 24px !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
            background-color: rgba(255,255,255,0.08) !important;
            color:            #e3e3e3 !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] > div { background-color: transparent !important; }

        /* ── selectbox ── */
        [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
            background-color: #2c2d30 !important;
            color:            #e3e3e3 !important;
            border:           1px solid rgba(255,255,255,0.12) !important;
            border-radius:    8px !important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] span,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] p {
            color: #e3e3e3 !important; -webkit-text-fill-color: #e3e3e3 !important;
        }
        [data-testid="stSidebar"] [data-testid="stSelectbox"] svg { fill: #9aa0a6 !important; }

        /* ── 공유 텍스트 영역 ── */
        [data-testid="stSidebar"] textarea {
            background-color: #2c2d30 !important;
            color:            #bdc1c5 !important;
            border:           1px solid rgba(255,255,255,0.1) !important;
            border-radius:    6px !important;
            font-size:        0.75rem !important;
        }

        /* ── 하단 링크 ── */
        .sb-bottom {
            padding-top: 10px;
            border-top:  1px solid rgba(255,255,255,0.07);
            flex-shrink: 0;
        }
        .sb-bottom-link {
            display:       flex;
            align-items:   center;
            gap:           10px;
            padding:       7px 6px;
            color:         #9aa0a6;
            font-size:     0.83rem;
            cursor:        pointer;
            border-radius: 6px;
            transition:    background 0.15s;
        }
        .sb-bottom-link:hover { background-color: rgba(255,255,255,0.07); color: #e3e3e3; }

        header, footer { background-color: transparent !important; }

        /* ── 사이드바 상단 아이콘 바 (Gemini 스타일) ── */
        .sb-topbar {
            display:         flex;
            align-items:     center;
            justify-content: space-between;
            padding:         6px 2px 10px;
            flex-shrink:     0;
        }
        .sb-topbar-icon {
            width:           36px;
            height:          36px;
            display:         inline-flex;
            align-items:     center;
            justify-content: center;
            font-size:       18px;
            border-radius:   50%;
            cursor:          pointer;
            color:           #9aa0a6;
            transition:      background 0.15s;
        }
        .sb-topbar-icon:hover { background: rgba(255,255,255,0.08); color: #e3e3e3; }
        .sb-app-name { font-size: 0.78rem; color: #9aa0a6 !important; -webkit-text-fill-color: #9aa0a6 !important; letter-spacing: 0.3px; }

        .welcome-container {
            display:        flex;
            flex-direction: column;
            align-items:    center;
            text-align:     center;
            width:          100%;
            margin-top:     20vh;
        }

        .welcome-title {
            font-size:   2.8rem !important;
            font-weight: 500 !important;
            background:  linear-gradient(74deg, #4285f4 0, #9b72cb 9%, #d96570 20%, #e3e3e3 40%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.05rem !important;
            line-height: 1.3 !important;
        }

        .welcome-subtitle {
            font-size:   2.8rem !important;
            font-weight: 500 !important;
            color:       #444746 !important;
            -webkit-text-fill-color: #444746 !important;
            margin-top:    0 !important;
            margin-bottom: 2rem !important;
            line-height:   1.3 !important;
        }

        /* 퀘스타일 텝스트 입력 컴포넌트 (웹쾘스타일 입력창 대체) */
        .welcome-input-row {
            width:         min(680px, 100%);
            background:    #2c2d30;
            border:        1px solid rgba(255,255,255,0.13);
            border-radius: 26px;
            padding:       10px 14px 10px 22px;
            display:       flex;
            align-items:   center;
            gap:           8px;
            margin-bottom: 1.2rem;
            box-shadow:    0 2px 10px rgba(0,0,0,0.5);
        }

        /* 액션 칩 버튼 (Gemini 칩 스타일) — 메인 컨텐츠 컬럼 내 버튼만 적용 */
        [data-testid="stMainBlockContainer"] [data-testid="column"] div.stButton > button {
            background-color: #2c2d30 !important;
            color:            #c4c7cc !important;
            border:           1px solid rgba(255,255,255,0.10) !important;
            border-radius:    20px !important;
            font-size:        0.82rem !important;
            padding:          8px 10px !important;
            min-height:       0 !important;
            height:           auto !important;
            white-space:      nowrap !important;
            font-weight:      400 !important;
            overflow:         hidden !important;
            text-overflow:    ellipsis !important;
        }
        [data-testid="stMainBlockContainer"] [data-testid="column"] div.stButton > button:hover {
            background-color: #3c4043 !important;
            color:            #e3e3e3 !important;
        }

        /* ════════════════════════════════════════════════════
           [GEMINI 벤치마크] 하단 입력 영역 완전 다크 처리
           stBottom 내부 모든 요소를 다크로 초기화한 뒤
           입력 pill만 #2c2d30 컨테이너로 재스타일
        ════════════════════════════════════════════════════ */

        /* ① stBottom 전체 + 모든 자손 배경 강제 다크 */
        [data-testid="stBottom"],
        [data-testid="stBottom"] > *,
        [data-testid="stBottom"] > * > *,
        [data-testid="stBottom"] > * > * > *,
        [data-testid="stBottom"] > * > * > * > *,
        [data-testid="stBottomBlockContainer"],
        [data-testid="stBottomBlockContainer"] > *,
        [data-testid="stBottomBlockContainer"] > * > *,
        [data-testid="stChatInputContainer"],
        [data-testid="stChatInputContainer"] > *,
        [data-testid="stChatInputContainer"] > * > *,
        [data-testid="stChatInputContainer"] > * > * > * {
            background-color: #131314 !important;
            background:       #131314 !important;
            border-color: transparent !important;
            box-shadow: none !important;
        }

        /* ② 입력창 컨테이너 — flex 가운데 정렬 (Gemini 방식) */
        [data-testid="stChatInputContainer"] {
            display:         flex !important;
            justify-content: center !important;
            align-items:     center !important;
            width:           100% !important;
            padding:         0 2rem 1rem !important;
            background-color: #131314 !important;
        }

        /* ② 입력 pill — Gemini 스타일: 짙은 회색 라운드 컨테이너 */
        [data-testid="stChatInput"] {
            background-color: #2c2d30 !important;
            background:       #2c2d30 !important;
            border:        1px solid rgba(255,255,255,0.15) !important;
            border-radius: 26px !important;
            padding:       8px 16px 8px 20px !important;
            box-shadow:    0 2px 12px rgba(0,0,0,0.6) !important;
            width:         min(760px, 100%) !important;
            max-width:     760px !important;
            margin:        0 auto !important;
            flex-shrink:   0 !important;
        }

        /* ③ pill 내부 모든 자손 배경 투명 (pill 색이 보이도록) */
        [data-testid="stChatInput"] > *,
        [data-testid="stChatInput"] > * > *,
        [data-testid="stChatInput"] > * > * > *,
        [data-testid="stChatInput"] form,
        [data-testid="stChatInput"] form > *,
        [data-testid="stChatInput"] label,
        [data-testid="stChatInput"] div {
            background-color: transparent !important;
            background:       transparent !important;
            border-color: transparent !important;
            box-shadow: none !important;
        }

        /* ④ textarea 텍스트 — 밝은 흰색, 커서 파란색 */
        [data-testid="stChatInput"] textarea {
            background-color: transparent !important;
            background:       transparent !important;
            color:            #f0f0f0 !important;
            -webkit-text-fill-color: #f0f0f0 !important;
            caret-color:      #8ab4f8 !important;
            font-size:        1rem !important;
            font-weight:      400 !important;
            line-height:      1.6 !important;
            padding:          10px 0 !important;
            border:           none !important;
            outline:          none !important;
            /* 브라우저 기본 흰 배경 완전 차단 */
            color-scheme:     dark !important;
        }

        /* ⑤ placeholder 텍스트 — 직접적으로 밝게 */
        [data-testid="stChatInput"] textarea::placeholder {
            color:            #9aa0a6 !important;
            -webkit-text-fill-color: #9aa0a6 !important;
            opacity:          1 !important;
        }

        /* ⑥ 전송 버튼 */
        [data-testid="stChatInput"] button {
            background-color: transparent !important;
            border: none !important;
        }
        [data-testid="stChatInput"] button svg,
        [data-testid="stChatInput"] button svg path {
            fill:   #8ab4f8 !important;
            stroke: #8ab4f8 !important;
        }

        /* ⑦ 포커스 글로우 */
        [data-testid="stChatInput"]:focus-within {
            border-color: #8ab4f8 !important;
            box-shadow:   0 0 0 3px rgba(138,180,248,0.18),
                          0 2px 12px rgba(0,0,0,0.6) !important;
        }

        /* ⑧ InputInstructions (글자수/안내) */
        [data-testid="InputInstructions"],
        [data-testid="InputInstructions"] * {
            color:            #5f6368 !important;
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
            border-bottom: 1px solid rgba(255,255,255,0.05) !important;
        }

        /* 스트리밍 커서 블링크 효과 */
        @keyframes cursorBlink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }

        /* ══════════════════════════════════════════════════
           채팅 메시지 배경 강제 투명화 (흰 배경 완전 차단)
        ══════════════════════════════════════════════════ */
        .stChatMessage,
        .stChatMessage > div,
        .stChatMessage .element-container,
        [data-testid="stChatMessage"],
        [data-testid="stChatMessage"] > div,
        [data-testid="stChatMessageContent"] {
            background-color: transparent !important;
            background: transparent !important;
        }

        /* ══════════════════════════════════════════════════
           채팅 텍스트 전체 가시성 강화 (모든 자식 요소 포함)
        ══════════════════════════════════════════════════ */
        .stChatMessage * {
            color: #e3e3e3 !important;
            -webkit-text-fill-color: #e3e3e3 !important;
        }

        .stChatMessage [data-testid="stMarkdownContainer"],
        .stChatMessage [data-testid="stMarkdownContainer"] p,
        .stChatMessage [data-testid="stMarkdownContainer"] li,
        .stChatMessage [data-testid="stMarkdownContainer"] span,
        .stChatMessage [data-testid="stMarkdownContainer"] div,
        .stChatMessage [data-testid="stText"],
        .stChatMessage [data-testid="stText"] p,
        .stChatMessage [data-testid="stText"] span {
            color: #e3e3e3 !important;
            -webkit-text-fill-color: #e3e3e3 !important;
            font-size: 1.05rem !important;
            line-height: 1.85 !important;
            background-color: transparent !important;
        }

        .stChatMessage [data-testid="stMarkdownContainer"] h1,
        .stChatMessage [data-testid="stMarkdownContainer"] h2,
        .stChatMessage [data-testid="stMarkdownContainer"] h3,
        .stChatMessage [data-testid="stMarkdownContainer"] h4,
        .stChatMessage [data-testid="stMarkdownContainer"] h5,
        .stChatMessage [data-testid="stMarkdownContainer"] strong,
        .stChatMessage [data-testid="stMarkdownContainer"] b {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            font-weight: 700 !important;
        }

        /* 사용자 메시지 버블 (오른쪽 정렬) */
        [data-testid="stChatMessage"][data-role="user"] {
            justify-content: flex-end !important;
        }

        [data-testid="stChatMessage"][data-role="user"] [data-testid="stMarkdownContainer"] p {
            background: rgba(138, 180, 248, 0.12) !important;
            border: 1px solid rgba(138, 180, 248, 0.2) !important;
            padding: 12px 18px !important;
            border-radius: 20px 20px 4px 20px !important;
            display: inline-block !important;
        }

        /* 어시스턴트 응답 텍스트 구분선 효과 */
        [data-testid="stChatMessage"][data-role="assistant"] [data-testid="stMarkdownContainer"] {
            border-left: 2px solid rgba(138, 180, 248, 0.3) !important;
            padding-left: 16px !important;
            margin-left: 4px !important;
        }

        [data-testid="stChatMessageAvatar"] {
            background-color: #2a2b2e !important;
            border: 1px solid #444 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # ── components.html(): JS로 document.head 맨 끝에 style 주입 (emotion CSS 이후 → 확실히 이김) ──
    components.html("""
<script>
(function() {
    var SID = 'woochi-sb-fix';
    function run() {
        var doc = window.parent.document;
        if (!doc) return;
        var old = doc.getElementById(SID);
        if (old) old.parentNode.removeChild(old);
        var sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) { setTimeout(run, 300); return; }
        var s = doc.createElement('style');
        s.id = SID;
        s.textContent = [
            '[data-testid="stSidebar"] * {',
            '  margin: 0 !important;',
            '  padding: 0 !important;',
            '  gap: 0 !important;',
            '  min-height: 0 !important;',
            '  border: none !important;',
            '  box-shadow: none !important;',
            '  background-color: transparent !important;',
            '  background: transparent !important;',
            '}',
            '[data-testid="stSidebar"] button {',
            '  min-height: 32px !important;',
            '  padding: 4px 10px !important;',
            '}',
            '[data-testid="stSidebarContent"] {',
            '  padding: 8px 4px !important;',
            '}'
        ].join('\\n');
        doc.head.appendChild(s);
    }
    run();
})();
</script>
""", height=0)

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
    _default_strategy = "recursive"
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--strategy" and i + 1 < len(sys.argv):
                _default_strategy = sys.argv[i + 1]
    if "strategy" not in st.session_state:
        st.session_state.strategy = _default_strategy
    strategy = st.session_state.strategy

    with st.sidebar:
        # ── 헤더: CSS-only 로고 (SVG 새니타이저 우회) ──────────
        st.markdown("""
            <div class="sb-topbar">
                <div style="display:flex;align-items:center;gap:6px;">
                    <span class="sb-topbar-icon" title="메뉴">☰</span>
                    <span class="sb-app-name">전우치 명상소</span>
                </div>
                <span class="sb-topbar-icon" title="검색">🔍</span>
            </div>
        """, unsafe_allow_html=True)

        # ── 새 채팅 버튼 ────────────────────────────────────────
        if st.button("✏️  새 채팅", use_container_width=True,
                     key="new_chat_btn", type="primary"):
            st.session_state.messages = []
            st.session_state.current_session_id = None
            st.session_state.show_welcome  = True
            st.session_state.menu_open_sid = None
            st.session_state.rename_sid    = None
            st.session_state.share_sid     = None
            st.rerun()

        # ── session_state 초기화 ─────────────────────────────────
        for _k in ("menu_open_sid", "rename_sid", "share_sid"):
            if _k not in st.session_state:
                st.session_state[_k] = None

        # ── DB 조회 및 분류 ──────────────────────────────────────
        sessions    = db_get_sessions(limit=40)
        current_sid = st.session_state.get("current_session_id")
        menu_sid    = st.session_state.menu_open_sid
        rename_sid  = st.session_state.rename_sid
        share_sid   = st.session_state.share_sid

        pinned_sessions = [(s, t, p, c) for s, t, p, c in sessions if p]
        recent_sessions = [(s, t, p, c) for s, t, p, c in sessions if not p]

        def _render_sessions(items):
            for sid, title, is_pinned, _dt in items:
                is_active = (sid == current_sid)

                # ── 이름 변경 모드 ──────────────────────────────
                if rename_sid == sid:
                    new_t = st.text_input(
                        "", value=title, key=f"ri_{sid}",
                        label_visibility="collapsed",
                        placeholder="새 이름 입력…"
                    )
                    rc1, rc2 = st.columns([1, 1], gap="small")
                    with rc1:
                        if st.button("저장", key=f"rs_{sid}",
                                     use_container_width=True, type="primary"):
                            db_rename_session(sid, new_t.strip() or title)
                            st.session_state.rename_sid = None
                            st.rerun()
                    with rc2:
                        if st.button("취소", key=f"rc_{sid}",
                                     use_container_width=True):
                            st.session_state.rename_sid = None
                            st.rerun()
                    continue

                # ── 일반 행: [타이틀] [⋮] ───────────────────────
                label = ("📌 " if is_pinned else "") + ("● " if is_active else "") + title
                c1, c2 = st.columns([8, 1], gap="small")
                with c1:
                    if st.button(label, key=f"s_{sid}",
                                 use_container_width=True):
                        st.session_state.messages = db_load_messages(sid)
                        st.session_state.current_session_id = sid
                        st.session_state.show_welcome  = False
                        st.session_state.menu_open_sid = None
                        st.rerun()
                with c2:
                    icon = "✕" if menu_sid == sid else "⋮"
                    if st.button(icon, key=f"m_{sid}",
                                 use_container_width=True):
                        st.session_state.menu_open_sid = (
                            None if menu_sid == sid else sid
                        )
                        st.rerun()

                # ── 컨텍스트 메뉴 ───────────────────────────────
                if menu_sid == sid:
                    st.markdown('<div class="sb-ctx-divider"></div>',
                                unsafe_allow_html=True)
                    if st.button("  ✏️  이름 변경", key=f"mr_{sid}",
                                 use_container_width=True):
                        st.session_state.rename_sid    = sid
                        st.session_state.menu_open_sid = None
                        st.rerun()
                    pin_lbl = "  📌  고정 해제" if is_pinned else "  📌  고정"
                    if st.button(pin_lbl, key=f"mp_{sid}",
                                 use_container_width=True):
                        db_pin_session(sid, not is_pinned)
                        st.session_state.menu_open_sid = None
                        st.rerun()
                    if st.button("  🔗  대화 공유", key=f"msh_{sid}",
                                 use_container_width=True):
                        st.session_state.share_sid     = sid
                        st.session_state.menu_open_sid = None
                        st.rerun()
                    if st.button("  🗑️  삭제", key=f"md_{sid}",
                                 use_container_width=True):
                        db_delete_session(sid)
                        if current_sid == sid:
                            st.session_state.messages = []
                            st.session_state.current_session_id = None
                            st.session_state.show_welcome = True
                        st.session_state.menu_open_sid = None
                        st.rerun()
                    st.markdown('<div class="sb-ctx-divider"></div>',
                                unsafe_allow_html=True)

        # ── 고정 섹션 ────────────────────────────────────────────
        if pinned_sessions:
            st.markdown('<div class="sb-section-title">📌 고정</div>',
                        unsafe_allow_html=True)
            _render_sessions(pinned_sessions)

        # ── 채팅 섹션 ───────────────────────────────────────────────
        if recent_sessions:
            st.markdown('<div class="sb-section-title">채팅</div>',
                        unsafe_allow_html=True)
            _render_sessions(recent_sessions)
        elif not pinned_sessions:
            st.markdown('<div class="sb-empty">아직 대화 내역이 없습니다</div>',
                        unsafe_allow_html=True)

        # ── 공유 박스 ────────────────────────────────────────────
        if share_sid:
            share_msgs = db_load_messages(share_sid)
            share_text = "\n\n".join(
                f"{'나' if m['role'] == 'user' else '전우치'}: {m['content']}"
                for m in share_msgs
            )
            st.markdown('<div class="sb-section-title">🔗 대화 공유</div>',
                        unsafe_allow_html=True)
            st.text_area("", value=share_text, height=160,
                         key="share_ta", label_visibility="collapsed")
            if st.button("닫기", key="share_close", use_container_width=True):
                st.session_state.share_sid = None
                st.rerun()

        # ── 스페이서 + 설정 + 하단 링크 ─────────────────────────
        st.markdown('<div class="sb-spacer"></div>', unsafe_allow_html=True)

        with st.expander("⚙️  설정"):
            st.markdown(
                '<div style="font-size:0.8rem;color:#9aa0a6;margin-bottom:6px;">검색 전략</div>',
                unsafe_allow_html=True)
            new_strategy = st.selectbox(
                "검색 전략",
                ("recursive", "semantic", "heading"),
                index=("recursive", "semantic", "heading").index(strategy),
                key="strategy_select",
                label_visibility="collapsed"
            )
            if new_strategy != strategy:
                st.session_state.strategy = new_strategy
                strategy = new_strategy

        st.markdown("""
            <div class="sb-bottom">
                <div class="sb-bottom-link">🕒 활동</div>
                <div class="sb-bottom-link">❓ 도움말</div>
            </div>
        """, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True

    # current_session_id: DB에 저장된 현재 세션 id (없으면 None)
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None

    if st.session_state.show_welcome and len(st.session_state.messages) == 0:
        st.markdown("""
        <div class="welcome-container">
            <h1 class="welcome-title">준영님, 안녕하세요</h1>
            <h1 class="welcome-subtitle">무엇을 도와드릴까요?</h1>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(6)
        actions = [
            ("🧘", "명상 시작"),
            ("📝", "고민 상담"),
            ("📖", "지혜 찾기"),
            ("✨", "무드 명상"),
            ("🌬", "숨결 수련"),
            ("🌙", "스트레스 완화"),
        ]
        for i, (icon, label) in enumerate(actions):
            with cols[i]:
                if st.button(f"{icon} {label}", key=f"action_{i}", use_container_width=True):
                    sid = db_create_session(label)
                    st.session_state.current_session_id = sid
                    db_add_message(sid, "user", label)
                    st.session_state.messages.append({"role": "user", "content": label})
                    st.session_state.show_welcome = False
                    st.rerun()

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
        # ① 세션이 없으면 DB에 새 세션 생성
        if st.session_state.current_session_id is None:
            sid = db_create_session(prompt)
            st.session_state.current_session_id = sid
        # ② 사용자 메시지 DB 저장
        db_add_message(st.session_state.current_session_id, "user", prompt)
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
                status_placeholder.empty()
                response = st.write_stream(agent.chat_stream(user_msg))
                # ③ 어시스턴트 응답 DB 저장
                if st.session_state.current_session_id is not None:
                    db_add_message(st.session_state.current_session_id, "assistant", response)
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
