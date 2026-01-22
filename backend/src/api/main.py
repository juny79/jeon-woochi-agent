from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from src.agent.orchestrator import JeonWoochiAgent
from src.agent.persona_prompt import JeonWoochiPersona
from src.vector_store.manager import VectorDBManager
from src.retriever.hybrid_retriever import HybridRetriever
from src.qa.engine import QAEngine
from src.config import Config
import uvicorn

app = FastAPI(title="JeonWoochi API", description="전우치 명상 에이전트 백엔드")

# CORS 설정 (Next.js 프론트엔드 연결 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RAG 엔진 캐싱
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
    strategy: Optional[str] = "recursive"

class ChatResponse(BaseModel):
    response: str

@app.get("/")
async def root():
    return {"status": "ok", "message": "JeonWoochi API is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        agent = get_agent(request.strategy)
        response = agent.chat(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
