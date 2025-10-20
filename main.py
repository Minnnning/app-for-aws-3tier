import os
from typing import List
from datetime import datetime
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- 1. 환경 변수에서 데이터베이스 연결 정보 가져오기 ---
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "newdb")

# 환경 변수를 사용하여 데이터베이스 연결 URL을 동적으로 생성합니다.
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"Connecting to database at: {DB_HOST}:{DB_PORT}")

# 데이터베이스 엔진 생성
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 데이터베이스 모델 정의 ---
class SimpleData(Base):
    __tablename__ = "simple_data"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 데이터베이스에 테이블 생성
Base.metadata.create_all(bind=engine)

# --- Pydantic 모델 (데이터 유효성 검사) ---
class DataItemCreate(BaseModel):
    content: str

class DataItem(BaseModel):
    id: int
    content: str
    created_at: datetime
    class Config:
        from_attributes = True

# FastAPI 앱 인스턴스 생성
app = FastAPI()

# --- CORS 미들웨어 추가 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 데이터베이스 세션 의존성 주입 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API 엔드포인트 ---
def read_root():
    # HOSTNAME 환경 변수가 있으면 그 값을, 없으면 'N/A'를 사용
    # EC2나 컨테이너 환경에서는 보통 HOSTNAME이 자동으로 설정됩니다.
    hostname = os.getenv('HOSTNAME', 'N/A')
    return {"message": f"Server is running on {hostname}"}

@app.post("/api/data", response_model=DataItem)
def create_data_entry(item: DataItemCreate, db: sqlalchemy.orm.Session = Depends(get_db)):
    """
    새로운 데이터를 생성합니다.
    """
    db_entry = SimpleData(content=item.content)
    try:
        db.add(db_entry)
        db.commit()
        db.refresh(db_entry)
        return db_entry
    except Exception as e:
        db.rollback()
        print(f"DB 저장 오류: {e}")
        raise HTTPException(status_code=500, detail="데이터베이스 저장에 실패했습니다.")

@app.get("/api/data", response_model=List[DataItem])
def read_data_entries(skip: int = 0, limit: int = 100, db: sqlalchemy.orm.Session = Depends(get_db)):
    """
    저장된 모든 데이터를 조회합니다. (최신순)
    """
    entries = db.query(SimpleData).order_by(SimpleData.created_at.desc()).offset(skip).limit(limit).all()
    return entries

# --- 2. 새로 추가된 데이터 삭제 기능 ---
@app.delete("/api/data/{item_id}", response_model=dict)
def delete_data_entry(item_id: int, db: sqlalchemy.orm.Session = Depends(get_db)):
    """
    특정 ID의 데이터를 삭제합니다.
    """
    # 1. 삭제할 데이터 조회
    db_entry = db.query(SimpleData).filter(SimpleData.id == item_id).first()

    # 2. 데이터가 없는 경우 404 오류 반환
    if db_entry is None:
        raise HTTPException(status_code=404, detail="해당 ID의 데이터를 찾을 수 없습니다.")

    # 3. 데이터 삭제 및 변경사항 커밋
    try:
        db.delete(db_entry)
        db.commit()
        return {"message": f"데이터(ID: {item_id})가 성공적으로 삭제되었습니다."}
    except Exception as e:
        db.rollback() # 오류 발생 시 롤백
        print(f"DB 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail="데이터베이스 삭제에 실패했습니다.")
