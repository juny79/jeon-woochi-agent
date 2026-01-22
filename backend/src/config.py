import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SOLAR_API_KEY = os.getenv("SOLAR_API_KEY")
    DB_PATH = "./data/chroma_db"
    COLLECTION_NAME = "meditation_knowledge"
    # 팀 B, C, D가 공통으로 참조할 설정들

    # [▼ 새로 추가해야 할 부분]
    # 청킹(Chunking) 설정
    CHUNK_SIZE = 500       # 문서를 500자 단위로 자름
    CHUNK_OVERLAP = 50     # 문맥 유지를 위해 50자씩 겹치게 자름