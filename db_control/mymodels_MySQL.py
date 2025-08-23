# --- START OF FILE mymodels_MySQL.py ---

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
    Date,
    Boolean,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional, List
from datetime import datetime


# 親クラス
class Base(DeclarativeBase):
    pass


## 以下、子クラスの定義
# USERSテーブル: ユーザー情報を格納する
class USERS(Base):
    __tablename__ = "users"

    # ユーザーを一意に識別するID (主キー)
    user_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="ユーザーID"
    )
    # 一意のユーザーネーム (例: pattyo_tokyogas)
    username: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="ユーザーネーム"
    )
    # 表示名
    display_name: Mapped[Optional[str]] = mapped_column(String(255), comment="表示名")
    # 一意のメールアドレス
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="メールアドレス"
    )
    # ハッシュ化されたパスワード (ソーシャルログインの場合はNULL)
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), comment="ハッシュ化されたパスワード"
    )
    # プロフィール画像のURL
    profile_image_url: Mapped[Optional[str]] = mapped_column(
        String(255), comment="プロフィール画像URL"
    )
    # 自己紹介文
    bio: Mapped[Optional[str]] = mapped_column(Text, comment="自己紹介文")
    # 居住エリア (例: 東京都江東区)
    area: Mapped[Optional[str]] = mapped_column(String(255), comment="居住エリア")
    # 性別
    gender: Mapped[Optional[str]] = mapped_column(String(50), comment="性別")
    # 生年月日
    birthdate: Mapped[Optional[datetime]] = mapped_column(Date, comment="生年月日")
    # 東京ガスお客さま番号 (NULL許容)
    tokyo_gas_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), comment="東京ガスお客さま番号"
    )
    # ユーザー種別 (例: tokyogas_member, general)
    user_type: Mapped[str] = mapped_column(
        String(50), default="general", comment="ユーザー種別"
    )
    # レコード作成日時 (自動設定)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )
    # レコード更新日時 (自動更新)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新日時",
    )

    # --- リレーションの定義 ---
    social_logins: Mapped[List["SOCIAL_LOGINS"]] = relationship(
        "SOCIAL_LOGINS", back_populates="user"
    )
    posts: Mapped[List["POSTS"]] = relationship("POSTS", back_populates="user")
    likes: Mapped[List["LIKES"]] = relationship("LIKES", back_populates="user")
    comments: Mapped[List["COMMENTS"]] = relationship("COMMENTS", back_populates="user")
    bookmarks: Mapped[List["BOOKMARKS"]] = relationship(
        "BOOKMARKS", back_populates="user"
    )
    following: Mapped[List["FOLLOWS"]] = relationship(
        "FOLLOWS", foreign_keys="FOLLOWS.follower_id", back_populates="follower"
    )
    followers: Mapped[List["FOLLOWS"]] = relationship(
        "FOLLOWS", foreign_keys="FOLLOWS.following_id", back_populates="following"
    )
    notifications_received: Mapped[List["NOTIFICATIONS"]] = relationship(
        "NOTIFICATIONS",
        foreign_keys="NOTIFICATIONS.recipient_user_id",
        back_populates="recipient",
    )
    notifications_sent: Mapped[List["NOTIFICATIONS"]] = relationship(
        "NOTIFICATIONS",
        foreign_keys="NOTIFICATIONS.actor_user_id",
        back_populates="actor",
    )
    survey_responses: Mapped[List["SURVEY_RESPONSES"]] = relationship(
        "SURVEY_RESPONSES", back_populates="user"
    )


# SOCIAL_LOGINSテーブル: ソーシャルログイン情報を格納する
class SOCIAL_LOGINS(Base):
    __tablename__ = "social_logins"
    # 関連するユーザーのID (複合主キー、外部キー)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), primary_key=True, comment="ユーザーID"
    )
    # 認証プロバイダー (例: Google, Apple) (複合主キー)
    provider: Mapped[str] = mapped_column(
        String(50), primary_key=True, comment="認証プロバイダー"
    )
    # プロバイダー固有のID
    provider_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment="プロバイダー固有のID"
    )

    user: Mapped["USERS"] = relationship("USERS", back_populates="social_logins")


# POSTSテーブル: 投稿内容を格納する
class POSTS(Base):
    __tablename__ = "posts"
    post_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="投稿ID")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), comment="投稿者ID"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="投稿本文")

    # カテゴリフラグ
    is_follow_category: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="カテゴリ: フォロー (0 or 1)"
    )
    is_neighborhood_category: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="カテゴリ: ご近所さん (0 or 1)"
    )
    is_event_category: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="カテゴリ: イベント (0 or 1)"
    )
    is_gourmet_category: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="カテゴリ: グルメ (0 or 1)"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新日時"
    )

    user: Mapped["USERS"] = relationship("USERS", back_populates="posts")
    images: Mapped[List["POST_IMAGES"]] = relationship(
        "POST_IMAGES", back_populates="post", cascade="all, delete-orphan"
    )
    comments: Mapped[List["COMMENTS"]] = relationship(
        "COMMENTS", back_populates="post", cascade="all, delete-orphan"
    )
    likes: Mapped[List["LIKES"]] = relationship(
        "LIKES", back_populates="post", cascade="all, delete-orphan"
    )
    bookmarks: Mapped[List["BOOKMARKS"]] = relationship(
        "BOOKMARKS", back_populates="post", cascade="all, delete-orphan"
    )


# POST_IMAGESテーブル: 投稿に紐づく画像を格納する
class POST_IMAGES(Base):
    __tablename__ = "post_images"
    image_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, comment="画像ID"
    )
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.post_id"), comment="投稿ID")
    image_url: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="画像URL"
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, comment="表示順")

    post: Mapped["POSTS"] = relationship("POSTS", back_populates="images")


# COMMENTSテーブル: 投稿へのコメントを格納する
class COMMENTS(Base):
    __tablename__ = "comments"
    comment_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, comment="コメントID"
    )
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.post_id"), comment="投稿ID")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), comment="コメント投稿者ID"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="コメント本文")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    post: Mapped["POSTS"] = relationship("POSTS", back_populates="comments")
    user: Mapped["USERS"] = relationship("USERS", back_populates="comments")


# LIKESテーブル: 投稿への「いいね」を記録する
class LIKES(Base):
    __tablename__ = "likes"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), primary_key=True, comment="いいねしたユーザーID"
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.post_id"), primary_key=True, comment="いいねされた投稿ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    user: Mapped["USERS"] = relationship("USERS", back_populates="likes")
    post: Mapped["POSTS"] = relationship("POSTS", back_populates="likes")


# BOOKMARKSテーブル: 投稿のブックマークを記録する
class BOOKMARKS(Base):
    __tablename__ = "bookmarks"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
        primary_key=True,
        comment="ブックマークしたユーザーID",
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.post_id"),
        primary_key=True,
        comment="ブックマークされた投稿ID",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    user: Mapped["USERS"] = relationship("USERS", back_populates="bookmarks")
    post: Mapped["POSTS"] = relationship("POSTS", back_populates="bookmarks")


# FOLLOWSテーブル: ユーザー間のフォロー関係を記録する
class FOLLOWS(Base):
    __tablename__ = "follows"
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), primary_key=True, comment="フォローするユーザーID"
    )
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
        primary_key=True,
        comment="フォローされるユーザーID",
    )

    follower: Mapped["USERS"] = relationship(
        "USERS", foreign_keys=[follower_id], back_populates="following"
    )
    following: Mapped["USERS"] = relationship(
        "USERS", foreign_keys=[following_id], back_populates="followers"
    )


# SURVEYSテーブル: アンケートのマスタデータを格納する
class SURVEYS(Base):
    __tablename__ = "surveys"
    survey_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, comment="アンケートID"
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="アンケートタイトル"
    )
    question_text: Mapped[Optional[str]] = mapped_column(
        Text, comment="アンケートの質問文"
    )
    points: Mapped[int] = mapped_column(Integer, default=0, comment="獲得ポイント")
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment="回答締め切り"
    )
    target_audience: Mapped[str] = mapped_column(
        String(50), default="all", comment="対象者 (all, tokyogas_member)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    responses: Mapped[List["SURVEY_RESPONSES"]] = relationship(
        "SURVEY_RESPONSES", back_populates="survey"
    )


# SURVEY_RESPONSESテーブル: ユーザーのアンケート回答を記録する
class SURVEY_RESPONSES(Base):
    __tablename__ = "survey_responses"
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), primary_key=True, comment="回答者ID"
    )
    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.survey_id"), primary_key=True, comment="アンケートID"
    )
    choice: Mapped[str] = mapped_column(
        String(255), comment="回答選択 (agree, disagreeなど)"
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, comment="自由記述コメント")
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="回答日時"
    )

    user: Mapped["USERS"] = relationship("USERS", back_populates="survey_responses")
    survey: Mapped["SURVEYS"] = relationship("SURVEYS", back_populates="responses")


# NOTIFICATIONSテーブル: ユーザーへの通知を格納する
class NOTIFICATIONS(Base):
    __tablename__ = "notifications"
    notification_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, comment="通知ID"
    )
    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), comment="通知を受け取るユーザーID"
    )
    actor_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.user_id"), comment="通知の発生源となったユーザーID"
    )
    notification_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="通知種別 (like, comment, follow, new_survey)",
    )
    target_id: Mapped[Optional[int]] = mapped_column(
        Integer, comment="関連オブジェクトID (post_id, survey_idなど)"
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, comment="既読フラグ")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    recipient: Mapped["USERS"] = relationship(
        "USERS",
        foreign_keys=[recipient_user_id],
        back_populates="notifications_received",
    )
    actor: Mapped["USERS"] = relationship(
        "USERS", foreign_keys=[actor_user_id], back_populates="notifications_sent"
    )
