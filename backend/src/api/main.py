from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
from src.agent.orchestrator import JeonWoochiAgent
from src.agent.persona_prompt import JeonWoochiPersona
from src.vector_store.manager import VectorDBManager
from src.retriever.hybrid_retriever import HybridRetriever
from src.qa.engine import QAEngine
from src.config import Config
from src.db.base import engine, get_db, Base, SessionLocal
from src.db.models import ChatSession, ChatMessage
from sqlalchemy.orm import Session
import uvicorn

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(title="JeonWoochi API", description="전우치 명상 에이전트 백엔드")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_agents = {}

def get_agent(strategy: str = "recursive"):
    if strategy not in _agents:
        db_manager = VectorDBManager(api_key=Config.SOLAR_API_KEY, db_path=Config.DB_PATH)
        collection_name = f"meditation_{strategy}"
        hybrid_retriever = HybridRetriever(db_manager=db_manager, collection_name=collection_name)
        qa_engine = QAEngine(retriever=hybrid_retriever, api_key=Config.SOLAR_API_KEY)
        persona = JeonWoochiPersona.SYSTEM_PROMPT
        _agents[strategy] = JeonWoochiAgent(persona=persona, qa_engine=qa_engine)
    return _agents[strategy]

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    strategy: Optional[str] = "recursive"

class ChatResponse(BaseModel):
    response: str
    session_id: int

class SessionInfo(BaseModel):
    id: int
    title: str
    created_at: str

@app.get("/")
async def root():
    return {"status": "ok", "message": "JeonWoochi API is running"}

@app.get("/sessions", response_model=List[SessionInfo])
async def get_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at.isoformat()} for s in sessions]

@app.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    return [{"role": m.role, "content": m.content} for m in messages]

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        if request.session_id:
            session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            title = request.message[:20] + "..." if len(request.message) > 20 else request.message
            session = ChatSession(title=title)
            db.add(session)
            db.commit()
            db.refresh(session)

        user_msg = ChatMessage(session_id=session.id, role="user", content=request.message)
        db.add(user_msg)
        
        agent = get_agent(request.strategy)
        response = agent.chat(request.message)
        
        assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=response)
        db.add(assistant_msg)
        db.commit()
        
        return ChatResponse(response=response, session_id=session.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        if request.session_id:
            session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
        else:
            title = request.message[:20] + "..." if len(request.message) > 20 else request.message
            session = ChatSession(title=title)
            db.add(session)
            db.commit()
            db.refresh(session)

        # session.id를 미리 저장 (db session이 종료되기 전에)
        session_id = session.id

        user_msg = ChatMessage(session_id=session_id, role="user", content=request.message)
        db.add(user_msg)
        db.commit()

        agent = get_agent(request.strategy)

        async def event_generator():
            full_response = ""
            yield f"SESSION_ID:{session_id}\n"
            
            try:
                for chunk in agent.chat_stream(request.message):
                    if chunk:  # 빈 청크 필터링
                        full_response += chunk
                        # 각 청크를 UTF-8로 인코딩하여 전송
                        yield chunk.encode('utf-8').decode('utf-8')
            except Exception as e:
                print(f"Stream error: {e}")
                yield f"\n[오류] 스트리밍 중 문제 발생: {str(e)}"
            
            try:
                with SessionLocal() as save_db:
                    assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=full_response)
                    save_db.add(assistant_msg)
                    save_db.commit()
            except Exception as e:
                print(f"Error saving message: {e}")

        return StreamingResponse(event_generator(), media_type="text/plain; charset=utf-8")

    except Exception as e:
        print(f"Chat stream error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
