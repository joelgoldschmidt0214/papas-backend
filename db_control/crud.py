from sqlalchemy.orm import Session
from typing import List, Optional

from . import mymodels_MySQL as models
from passlib.context import CryptContext

# パスワードのハッシュ化と検証を行うためのコンテキストを設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    平文のパスワードを受け取り、ハッシュ化されたパスワード文字列を返します。

    Args:
        password (str): ハッシュ化する平文のパスワード。

    Returns:
        str: ハッシュ化されたパスワード文字列。
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    平文パスワードとハッシュ化されたパスワードを比較検証します。

    Args:
        plain_password (str): 検証する平文のパスワード。
        hashed_password (str): データベースに保存されているハッシュ化済みパスワード。

    Returns:
        bool: パスワードが一致すればTrue、そうでなければFalse。
    """
    return pwd_context.verify(plain_password, hashed_password)


# --- User CRUD ---


def get_user(db: Session, user_id: int) -> Optional[models.Users]:
    """
    ユーザーIDを指定して、単一のユーザー情報を取得します。

    Args:
        db (Session): データベースセッション。
        user_id (int): 取得したいユーザーのID。

    Returns:
        Optional[models.Users]: 見つかったユーザーオブジェクト。見つからなければNone。
    """
    return db.query(models.Users).filter(models.Users.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.Users]:
    """
    メールアドレスを指定して、単一のユーザー情報を取得します。

    Args:
        db (Session): データベースセッション。
        email (str): 取得したいユーザーのメールアドレス。

    Returns:
        Optional[models.Users]: 見つかったユーザーオブジェクト。見つからなければNone。
    """
    return db.query(models.Users).filter(models.Users.email == email).first()


def get_user_by_provider(
    db: Session, provider: str, provider_user_id: str
) -> Optional[models.Users]:
    """
    ソーシャルログイン情報（プロバイダ名とプロバイダ側ID）でユーザーを検索します。

    Args:
        db (Session): データベースセッション。
        provider (str): プロバイダ名 (例: 'google')。
        provider_user_id (str): プロバイダ側でのユーザー識別子。

    Returns:
        Optional[models.Users]: 見つかったユーザーオブジェクト。見つからなければNone。
    """
    # SocialLoginsテーブルから一致するレコードを検索
    social_login = (
        db.query(models.SocialLogins)
        .filter(
            models.SocialLogins.provider == provider,
            models.SocialLogins.provider_user_id == provider_user_id,
        )
        .first()
    )
    # レコードが存在すれば、関連するユーザーオブジェクトを返す
    if social_login:
        return social_login.user
    return None


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.Users]:
    """
    ユーザー情報の一覧を、ページネーション付きで取得します。

    Args:
        db (Session): データベースセッション。
        skip (int): スキップするレコード数。
        limit (int): 取得する最大レコード数。

    Returns:
        List[models.Users]: ユーザーオブジェクトのリスト。
    """
    return db.query(models.Users).offset(skip).limit(limit).all()


def create_user_with_password(db: Session, user_data: dict) -> models.Users:
    """
    メールアドレスとパスワードで新規ユーザーを作成します。

    Args:
        db (Session): データベースセッション。
        user_data (dict): 'email', 'username', 'password' を含む辞書。

    Returns:
        models.Users: 作成されたユーザーオブジェクト。
    """
    hashed_password = get_password_hash(user_data["password"])
    db_user = models.Users(
        email=user_data["email"],
        username=user_data["username"],
        password_hash=hashed_password,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_user_with_provider(
    db: Session, user_data: dict, provider_data: dict
) -> models.Users:
    """
    ソーシャルログインで新規ユーザーを作成、または既存ユーザーに連携させます。

    Args:
        db (Session): データベースセッション。
        user_data (dict): 'email', 'username' を含む辞書。
        provider_data (dict): 'provider', 'provider_user_id' を含む辞書。

    Returns:
        models.Users: 新規作成または連携されたユーザーオブジェクト。
    """
    # 同じメールアドレスのユーザーが既に存在するか検索
    db_user = get_user_by_email(db, email=user_data["email"])

    # ユーザーが存在しない場合は、パスワードなしで新規作成
    if not db_user:
        db_user = models.Users(
            email=user_data["email"],
            username=user_data["username"],
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    # SocialLoginsテーブルにソーシャルログイン情報を保存
    db_social_login = models.SocialLogins(
        user_id=db_user.id,
        provider=provider_data["provider"],
        provider_user_id=provider_data["provider_user_id"],
    )
    db.add(db_social_login)
    db.commit()

    return db_user


# --- Post CRUD ---


def get_posts(db: Session, skip: int = 0, limit: int = 100) -> List[models.Posts]:
    """
    投稿の一覧を、作成日時の降順（新しい順）でページネーション付きで取得します。

    Args:
        db (Session): データベースセッション。
        skip (int): スキップするレコード数。
        limit (int): 取得する最大レコード数。

    Returns:
        List[models.Posts]: 投稿オブジェクトのリスト。
    """
    return (
        db.query(models.Posts)
        .order_by(models.Posts.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def create_post(db: Session, content: str, user_id: int) -> models.Posts:
    """
    新しい投稿を作成し、データベースに保存します。

    Args:
        db (Session): データベースセッション。
        content (str): 投稿の本文。
        user_id (int): 投稿者のユーザーID。

    Returns:
        models.Posts: 作成された投稿オブジェクト。
    """
    db_post = models.Posts(content=content, user_id=user_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


# --- Like CRUD ---


def create_or_delete_like(db: Session, user_id: int, post_id: int) -> str:
    """
    投稿に「いいね」を追加、またはすでにあれば削除します（トグル動作）。

    Args:
        db (Session): データベースセッション。
        user_id (int): いいね操作を行うユーザーのID。
        post_id (int): いいね対象の投稿のID。

    Returns:
        str: 操作結果を示す文字列 ("liked" または "unliked")。
    """
    # 既にいいねが存在するか検索
    existing_like = (
        db.query(models.Likes)
        .filter(models.Likes.user_id == user_id, models.Likes.post_id == post_id)
        .first()
    )

    if existing_like:
        # いいねが存在すれば削除
        db.delete(existing_like)
        db.commit()
        return "unliked"
    else:
        # いいねが存在しなければ新規作成
        db_like = models.Likes(user_id=user_id, post_id=post_id)
        db.add(db_like)
        db.commit()
        return "liked"


# --- Comment CRUD ---


def create_comment(
    db: Session, content: str, user_id: int, post_id: int
) -> models.Comments:
    """
    投稿に新しいコメントを作成します。

    Args:
        db (Session): データベースセッション。
        content (str): コメントの本文。
        user_id (int): コメントを投稿するユーザーのID。
        post_id (int): コメント対象の投稿のID。

    Returns:
        models.Comments: 作成されたコメントオブジェクト。
    """
    db_comment = models.Comments(content=content, user_id=user_id, post_id=post_id)
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


# --- Bookmark CRUD ---


def create_or_delete_bookmark(db: Session, user_id: int, post_id: int) -> str:
    """
    投稿をブックマークに追加、またはすでにあれば削除します（トグル動作）。

    Args:
        db (Session): データベースセッション。
        user_id (int): ブックマーク操作を行うユーザーのID。
        post_id (int): ブックマーク対象の投稿のID。

    Returns:
        str: 操作結果を示す文字列 ("bookmarked" または "unbookmarked")。
    """
    # 既にブックマークが存在するか検索
    existing_bookmark = (
        db.query(models.Bookmarks)
        .filter(
            models.Bookmarks.user_id == user_id, models.Bookmarks.post_id == post_id
        )
        .first()
    )

    if existing_bookmark:
        # ブックマークが存在すれば削除
        db.delete(existing_bookmark)
        db.commit()
        return "unbookmarked"
    else:
        # ブックマークが存在しなければ新規作成
        db_bookmark = models.Bookmarks(user_id=user_id, post_id=post_id)
        db.add(db_bookmark)
        db.commit()
        return "bookmarked"
