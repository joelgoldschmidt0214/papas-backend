# crud.py

from sqlalchemy.orm import Session
from typing import List, Optional

# import mymodels_MySQL as models
from . import mymodels_MySQL as models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# --- User CRUD ---


def get_user(db: Session, user_id: int) -> Optional[models.Users]:
    return db.query(models.Users).filter(models.Users.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.Users]:
    return db.query(models.Users).filter(models.Users.email == email).first()


def get_user_by_provider(
    db: Session, auth_provider: str, provider_id: str
) -> Optional[models.Users]:
    """ソーシャルログイン用にプロバイダ情報でユーザーを検索"""
    return (
        db.query(models.Users)
        .filter(
            models.Users.auth_provider == auth_provider,
            models.Users.provider_id == provider_id,
        )
        .first()
    )


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.Users]:
    return db.query(models.Users).offset(skip).limit(limit).all()


def create_user_with_password(db: Session, user_data: dict) -> models.Users:
    """メール/パスワードで新規ユーザーを作成"""
    hashed_password = get_password_hash(user_data["password"])
    db_user = models.Users(
        email=user_data["email"],
        username=user_data["username"],
        password_hash=hashed_password,
        auth_provider="email",
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_user_with_provider(db: Session, user_data: dict) -> models.Users:
    """ソーシャルログインで新規ユーザーを作成"""
    db_user = models.Users(
        email=user_data["email"],
        username=user_data["username"],
        auth_provider=user_data["auth_provider"],
        provider_id=user_data["provider_id"],
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# --- Post CRUD ---


def get_posts(db: Session, skip: int = 0, limit: int = 100) -> List[models.Posts]:
    return (
        db.query(models.Posts)
        .order_by(models.Posts.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_post(db: Session, content: str, user_id: int) -> models.Posts:
    db_post = models.Posts(content=content, user_id=user_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


# --- Like CRUD ---


def create_or_delete_like(db: Session, user_id: int, post_id: int) -> str:
    """投稿に「いいね」する、または「いいね」を取り消す"""
    existing_like = (
        db.query(models.Likes)
        .filter(models.Likes.user_id == user_id, models.Likes.post_id == post_id)
        .first()
    )

    if existing_like:
        db.delete(existing_like)
        db.commit()
        return "unliked"
    else:
        db_like = models.Likes(user_id=user_id, post_id=post_id)
        db.add(db_like)
        db.commit()
        return "liked"
