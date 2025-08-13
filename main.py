from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# import requests
import json

# from db_control import crud, mymodels
from db_control import crud, mymodels_MySQL as mymodels  # 変更
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, Session
from db_control.connect_MySQL import engine

app = FastAPI()


# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World from FastAPI"}


# --- DB セッション依存関数 ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Pydantic スキーマ（Swagger 用） ---
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    auth_provider: str
    provider_id: Optional[str] = None


# --- Users エンドポイント ---
@app.get("/users", response_model=List[UserResponse], tags=["users"])
def list_users(
    skip: int = 0,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    users = crud.get_users(db, skip=skip, limit=limit)
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            created_at=u.created_at,
            auth_provider=u.auth_provider,
            provider_id=u.provider_id,
        )
        for u in users
    ]


@app.get("/users/{user_id}", response_model=UserResponse, tags=["users"])
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
        auth_provider=user.auth_provider,
        provider_id=user.provider_id,
    )
