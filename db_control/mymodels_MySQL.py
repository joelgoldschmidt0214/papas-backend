from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    BigInteger,
    PrimaryKeyConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional


# 親クラス
class Base(DeclarativeBase):
    pass


## 以下、子クラスの定義
# Userテーブル
class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="ユーザーID")
    username: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="ユーザー名"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="メールアドレス"
    )

    # パスワードハッシュはNULLを許容するように変更
    # ソーシャルログインのユーザーはこのカラムがNULLになる
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="ハッシュ化パスワード"
    )

    # ソーシャルログイン用のカラムを追加
    # 'google', 'apple', 'email' などの文字列を保存する
    auth_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="email", comment="認証プロバイダ"
    )

    # Google/Appleから提供される一意のIDを保存するカラム
    # これがパスワードの代わりになる
    provider_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, comment="プロバイダ固有のユーザーID"
    )

    ##以下、usersと、｛Post,Likes,Follows｝とのリレーションを定義
    # このユーザーが行った投稿 (一対多)
    posts: Mapped[list["Posts"]] = relationship("Posts", back_populates="user")
    # このユーザーが行ったいいね (一対多)
    likes: Mapped[list["Likes"]] = relationship("Likes", back_populates="user")
    # このユーザーがフォローしている人々の情報 (多対多)
    following: Mapped[list["Follows"]] = relationship(
        "Follows", foreign_keys="Follows.follower_id", back_populates="follower"
    )
    # このユーザーがフォローされている人々の情報 (多対多)
    followers: Mapped[list["Follows"]] = relationship(
        "Follows", foreign_keys="Follows.following_id", back_populates="following"
    )


# Postsテーブル: 投稿内容を格納
class Posts(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="投稿ID")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), comment="投稿者ID")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="投稿の本文")
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    # この投稿を行ったユーザー (多対一)
    user: Mapped["Users"] = relationship("Users", back_populates="posts")
    # この投稿についたいいね (一対多)
    likes: Mapped[list["Likes"]] = relationship("Likes", back_populates="post")
    # この投稿につけられたタグ (多対多の中間テーブル経由)
    post_tags: Mapped[list["PostTags"]] = relationship(
        "PostTags", back_populates="post"
    )


# Tagsテーブル: タグ名を格納
class Tags(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="タグID")
    name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="タグ名"
    )

    # このタグがつけられた投稿 (多対多の中間テーブル経由)
    post_tags: Mapped[list["PostTags"]] = relationship("PostTags", back_populates="tag")


# --- 中間テーブル ---
# 中間テーブルは、多対多の関係を表現するために使われます。
# Likesテーブル: 誰がどの投稿にいいねしたかを記録 (UsersとPostsの中間テーブル)
class Likes(Base):
    __tablename__ = "likes"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), comment="いいねしたユーザーID"
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id"), comment="いいねされた投稿ID"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    # 複合主キーの設定 (user_idとpost_idの組み合わせで一意)
    __table_args__ = (PrimaryKeyConstraint("user_id", "post_id"),)

    # 関連元のテーブル情報を取得するためのリレーション
    user: Mapped["Users"] = relationship("Users", back_populates="likes")
    post: Mapped["Posts"] = relationship("Posts", back_populates="likes")


# --- 中間テーブル ---
# Followsテーブル: フォロー関係を記録 (Usersテーブルの自己参照)
class Follows(Base):
    __tablename__ = "follows"

    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), comment="フォローしたユーザーID"
    )
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), comment="フォローされたユーザーID"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    # 複合主キーの設定
    __table_args__ = (PrimaryKeyConstraint("follower_id", "following_id"),)

    # 関連元のテーブル情報を取得するためのリレーション
    follower: Mapped["Users"] = relationship(
        "Users", foreign_keys=[follower_id], back_populates="following"
    )
    following: Mapped["Users"] = relationship(
        "Users", foreign_keys=[following_id], back_populates="followers"
    )


# --- 中間テーブル ---
# PostTagsテーブル: どの投稿にどのタグが付いているかを記録 (PostsとTagsの中間テーブル)
class PostTags(Base):
    __tablename__ = "post_tags"

    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), comment="投稿ID")
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), comment="タグID")

    # 複合主キーの設定
    __table_args__ = (PrimaryKeyConstraint("post_id", "tag_id"),)

    # 関連元のテーブル情報を取得するためのリレーション
    post: Mapped["Posts"] = relationship("Posts", back_populates="post_tags")
    tag: Mapped["Tags"] = relationship("Tags", back_populates="post_tags")
