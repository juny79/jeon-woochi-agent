from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 환경변수 DATABASE_URL이 있으면 PostgreSQL 사용 (Railway 배포 시)
# 없으면 SQLite 로컬 개발용 폴백
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jeon_woochi.db")

# PostgreSQL URL은 "postgres://"로 시작할 수 있어 SQLAlchemy 호환 형식으로 변환
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
