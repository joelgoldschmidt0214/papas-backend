# --- START OF FILE crud.py ---

from sqlalchemy.orm import Session
from typing import List, Optional

from sqlalchemy.orm import joinedload, selectinload

# as models とすることで、以降のコードで models.USERS のようにアクセスできる
from . import mymodels_MySQL as models
from passlib.context import CryptContext

# パスワードのハッシュ化と検証を行うためのコンテキストを設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """ヘルパー関数: 平文パスワードをハッシュ化します。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ヘルパー関数: 平文パスワードとハッシュを検証します。"""
    return pwd_context.verify(plain_password, hashed_password)


# --- User SELECT (Read) Operations ---


def select_user_by_id(db: Session, user_id: int) -> Optional[models.USERS]:
    """
    user_id を使用して単一のユーザーを取得します。
    """
    return db.query(models.USERS).filter(models.USERS.user_id == user_id).first()


def select_user_by_email(db: Session, email: str) -> Optional[models.USERS]:
    """
    メールアドレスを使用して単一のユーザーを取得します。
    """
    return db.query(models.USERS).filter(models.USERS.email == email).first()


def select_user_by_provider(
    db: Session, provider: str, provider_id: str
) -> Optional[models.USERS]:
    """
    ソーシャルログイン情報を使用してユーザーを取得します。
    """
    social_login = (
        db.query(models.SOCIAL_LOGINS)
        .filter(
            models.SOCIAL_LOGINS.provider == provider,
            models.SOCIAL_LOGINS.provider_id == provider_id,
        )
        .first()
    )
    if social_login:
        return social_login.user
    return None


def select_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.USERS]:
    """
    ページネーション付きでユーザーの一覧を取得します。
    """
    return db.query(models.USERS).offset(skip).limit(limit).all()


# --- User INSERT (Create) Operations ---


def insert_user_with_password(db: Session, user_data: dict) -> models.USERS:
    """
    ユーザー名、メールアドレス、パスワードを使用して新規ユーザーを登録します。
    """
    hashed_password = get_password_hash(user_data["password"])
    db_user = models.USERS(
        email=user_data["email"],
        username=user_data["username"],
        display_name=user_data.get("display_name"),
        password_hash=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# --- User UPDATE Operations ---


def update_user(
    db: Session, user_id: int, user_update_data: dict
) -> Optional[models.USERS]:
    """
    ユーザーの属性（表示名、自己紹介など）を更新します。
    """
    db_user = select_user_by_id(db, user_id=user_id)
    if db_user:
        for key, value in user_update_data.items():
            setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user


# --- Post SELECT (Read) Operations ---


def select_posts(db: Session, skip: int = 0, limit: int = 100) -> List[models.POSTS]:
    """
    投稿の一覧を作成日時の降順（新しい順）で取得します。
    関連データをEager LoadingしてN+1問題を回避します。
    """
    return (
        db.query(models.POSTS)
        .options(
            # to-oneリレーションはjoinedloadが効率的
            joinedload(models.POSTS.user),
            # to-manyリレーションはselectinloadが効率的
            selectinload(models.POSTS.images),
            selectinload(models.POSTS.likes),
            selectinload(models.POSTS.comments),
            selectinload(models.POSTS.bookmarks),
        )
        .order_by(models.POSTS.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def select_posts_by_user_id(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[models.POSTS]:
    """
    特定のユーザーによる投稿の一覧を取得します。
    """
    return (
        db.query(models.POSTS)
        .filter(models.POSTS.user_id == user_id)
        .order_by(models.POSTS.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def select_posts_by_tag_name(
    db: Session, tag_name: str, skip: int = 0, limit: int = 100
) -> List[models.POSTS]:
    """
    特定のカテゴリ名に関連付けられた投稿の一覧を取得します。
    """
    query = db.query(models.POSTS)

    # tag_nameに応じてフィルタリングするカラムを決定
    if tag_name == "フォロー":
        query = query.filter(models.POSTS.is_follow_category == True)
    elif tag_name == "ご近所さん":
        query = query.filter(models.POSTS.is_neighborhood_category == True)
    elif tag_name == "イベント":
        query = query.filter(models.POSTS.is_event_category == True)
    elif tag_name == "グルメ":
        query = query.filter(models.POSTS.is_gourmet_category == True)
    else:
        # 該当するカテゴリ名がない場合は空のリストを返す
        return []

    return (
        query.order_by(models.POSTS.created_at.desc()).offset(skip).limit(limit).all()
    )


# --- Post INSERT (Create) Operations ---


def insert_post(
    db: Session,
    content: str,
    user_id: int,
    is_follow: bool = False,
    is_neighborhood: bool = False,
    is_event: bool = False,
    is_gourmet: bool = False,
) -> models.POSTS:
    """
    指定されたユーザーの新しい投稿を作成します。カテゴリフラグも同時に設定します。
    """
    db_post = models.POSTS(
        content=content,
        user_id=user_id,
        is_follow_category=is_follow,
        is_neighborhood_category=is_neighborhood,
        is_event_category=is_event,
        is_gourmet_category=is_gourmet,
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


# --- Post DELETE Operations ---


def delete_post(db: Session, post_id: int, user_id: int) -> bool:
    """
    post_id を使用して投稿を削除します。ユーザーがその投稿の所有者であることを確認します。
    """
    db_post = (
        db.query(models.POSTS)
        .filter(models.POSTS.post_id == post_id, models.POSTS.user_id == user_id)
        .first()
    )
    if db_post:
        db.delete(db_post)
        db.commit()
        return True
    return False


# --- Comment Operations ---


def insert_comment(
    db: Session, content: str, user_id: int, post_id: int
) -> models.COMMENTS:
    """
    投稿に新しいコメントを追加します。
    """
    db_comment = models.COMMENTS(content=content, user_id=user_id, post_id=post_id)
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def select_comments_by_post_id(
    db: Session, post_id: int, skip: int = 0, limit: int = 100
) -> List[models.COMMENTS]:
    """
    特定の投稿に対するコメントの一覧を取得します。
    """
    return (
        db.query(models.COMMENTS)
        .filter(models.COMMENTS.post_id == post_id)
        .order_by(models.COMMENTS.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# --- Like Operations ---


def insert_or_delete_like(db: Session, user_id: int, post_id: int) -> str:
    """
    「いいね」が存在しない場合は追加し、存在する場合は削除します（トグル動作）。
    """
    existing_like = (
        db.query(models.LIKES)
        .filter(models.LIKES.user_id == user_id, models.LIKES.post_id == post_id)
        .first()
    )
    if existing_like:
        db.delete(existing_like)
        db.commit()
        return "deleted"
    else:
        db_like = models.LIKES(user_id=user_id, post_id=post_id)
        db.add(db_like)
        db.commit()
        return "inserted"


# --- Bookmark Operations ---


def insert_or_delete_bookmark(db: Session, user_id: int, post_id: int) -> str:
    """
    ブックマークが存在しない場合は追加し、存在する場合は削除します（トグル動作）。
    """
    existing_bookmark = (
        db.query(models.BOOKMARKS)
        .filter(
            models.BOOKMARKS.user_id == user_id, models.BOOKMARKS.post_id == post_id
        )
        .first()
    )
    if existing_bookmark:
        db.delete(existing_bookmark)
        db.commit()
        return "deleted"
    else:
        db_bookmark = models.BOOKMARKS(user_id=user_id, post_id=post_id)
        db.add(db_bookmark)
        db.commit()
        return "inserted"


def select_bookmarked_posts_by_user_id(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[models.POSTS]:
    """
    特定のユーザーがブックマークした投稿の一覧を取得します。
    """
    return (
        db.query(models.POSTS)
        .join(models.BOOKMARKS, models.POSTS.post_id == models.BOOKMARKS.post_id)
        .filter(models.BOOKMARKS.user_id == user_id)
        .order_by(models.BOOKMARKS.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# --- Follow Operations ---


def insert_or_delete_follow(db: Session, follower_id: int, following_id: int) -> str:
    """
    フォロー関係が存在しない場合は作成し、存在する場合は削除します（トグル動作）。
    """
    if follower_id == following_id:  # 自分自身はフォローできない
        return "error_self_follow"

    existing_follow = (
        db.query(models.FOLLOWS)
        .filter(
            models.FOLLOWS.follower_id == follower_id,
            models.FOLLOWS.following_id == following_id,
        )
        .first()
    )
    if existing_follow:
        db.delete(existing_follow)
        db.commit()
        return "deleted"  # unfollowed
    else:
        db_follow = models.FOLLOWS(follower_id=follower_id, following_id=following_id)
        db.add(db_follow)
        db.commit()
        return "inserted"  # followed


def select_followers(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[models.USERS]:
    """
    指定された user_id をフォローしているユーザーの一覧（フォロワー）を取得します。
    """
    return (
        db.query(models.USERS)
        .join(models.FOLLOWS, models.USERS.user_id == models.FOLLOWS.follower_id)
        .filter(models.FOLLOWS.following_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def select_following(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[models.USERS]:
    """
    指定された user_id がフォローしているユーザーの一覧を取得します。
    """
    return (
        db.query(models.USERS)
        .join(models.FOLLOWS, models.USERS.user_id == models.FOLLOWS.following_id)
        .filter(models.FOLLOWS.follower_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


# --- Survey Operations ---


def select_surveys(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.SURVEYS]:
    """
    全てのアンケートの一覧を取得します。
    """
    return db.query(models.SURVEYS).offset(skip).limit(limit).all()


def insert_survey(db: Session, survey_data: dict) -> models.SURVEYS:
    """
    新しいアンケートを作成します。
    """
    db_survey = models.SURVEYS(
        title=survey_data["title"],
        question_text=survey_data.get("question_text"),
        points=survey_data.get("points", 0),
    )
    db.add(db_survey)
    db.commit()
    db.refresh(db_survey)
    return db_survey


def insert_survey_response(db: Session, response_data: dict) -> models.SURVEY_RESPONSES:
    """
    ユーザーのアンケート回答を登録します。
    """
    db_response = models.SURVEY_RESPONSES(
        user_id=response_data["user_id"],
        survey_id=response_data["survey_id"],
        choice=response_data["choice"],
        comment=response_data.get("comment"),
    )
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    return db_response


def select_responses_by_survey_id(
    db: Session, survey_id: int, skip: int = 0, limit: int = 100
) -> List[models.SURVEY_RESPONSES]:
    """
    特定のアンケートに対する全ての回答を取得します。
    """
    return (
        db.query(models.SURVEY_RESPONSES)
        .filter(models.SURVEY_RESPONSES.survey_id == survey_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
