import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SOLAR_API_KEY = os.getenv("SOLAR_API_KEY")
    DB_PATH = "./data/chroma_db"
    COLLECTION_NAME = "meditation_knowledge"
    # 팀 B, C, D가 공통으로 참조할 설정들