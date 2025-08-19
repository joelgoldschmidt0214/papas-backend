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
# Userテーブル: ユーザー情報を格納する
class Users(Base):
    __tablename__ = "users"

    # ユーザーを一意に識別するID (主キー)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="ユーザーID")
    # ユーザー名 (ユニーク制約)
    username: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="ユーザー名"
    )
    # メールアドレス (ユニーク制約)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="メールアドレス"
    )
    # ハッシュ化されたパスワード (NULLを許容し、ソーシャルログイン等に対応)
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="ハッシュ化パスワード"
    )
    # プロフィール画像のURL
    profile_picture_url: Mapped[Optional[str]] = mapped_column(
        String(255), comment="プロフィール画像URL"
    )
    # 自己紹介文
    bio: Mapped[Optional[str]] = mapped_column(Text, comment="自己紹介")
    # 居住エリアや活動拠点
    location: Mapped[Optional[str]] = mapped_column(String(255), comment="居住エリア")
    # 性別
    gender: Mapped[Optional[str]] = mapped_column(String(50), comment="性別")
    # 生年月日
    birth_date: Mapped[Optional[datetime]] = mapped_column(Date, comment="生年月日")
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
    # このユーザーに紐づくソーシャルログイン情報 (一対多)
    social_logins: Mapped[List["SocialLogins"]] = relationship(
        "SocialLogins", back_populates="user"
    )
    # このユーザーが行った投稿 (一対多)
    posts: Mapped[List["Posts"]] = relationship("Posts", back_populates="user")
    # このユーザーが行ったいいね (一対多)
    likes: Mapped[List["Likes"]] = relationship("Likes", back_populates="user")
    # このユーザーが行ったコメント (一対多)
    comments: Mapped[List["Comments"]] = relationship("Comments", back_populates="user")
    # このユーザーが行ったブックマーク (一対多)
    bookmarks: Mapped[List["Bookmarks"]] = relationship(
        "Bookmarks", back_populates="user"
    )
    # このユーザーがフォローしているユーザーへの関連 (自己参照多対多)
    following: Mapped[List["Follows"]] = relationship(
        "Follows", foreign_keys="Follows.follower_id", back_populates="follower"
    )
    # このユーザーをフォローしているユーザーからの関連 (自己参照多対多)
    followers: Mapped[List["Follows"]] = relationship(
        "Follows", foreign_keys="Follows.following_id", back_populates="following"
    )
    # このユーザーが受信した通知 (受信者として)
    notifications_received: Mapped[List["Notifications"]] = relationship(
        "Notifications",
        foreign_keys="Notifications.recipient_user_id",
        back_populates="recipient",
    )
    # このユーザーが行ったアンケート回答
    questionnaire_answers: Mapped[List["UserQuestionnaireAnswers"]] = relationship(
        "UserQuestionnaireAnswers", back_populates="user"
    )


# SocialLoginsテーブル: ソーシャルログイン情報を格納する
class SocialLogins(Base):
    __tablename__ = "social_logins"

    # ソーシャルログイン情報を一意に識別するID (主キー)
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, comment="ソーシャルログインID"
    )
    # 関連するユーザーのID (外部キー)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), comment="ユーザーID")
    # ログインプロバイダー名 (例: 'google', 'apple')
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="プロバイダー (google, appleなど)"
    )
    # プロバイダー側でのユーザー識別子 (ユニーク制約)
    provider_user_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, comment="プロバイダーのユーザーID"
    )
    # レコード作成日時 (自動設定)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    # Usersテーブルへのリレーション
    user: Mapped["Users"] = relationship("Users", back_populates="social_logins")


# Postsテーブル: 投稿内容を格納する
class Posts(Base):
    __tablename__ = "posts"

    # 投稿を一意に識別するID (主キー)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="投稿ID")
    # 投稿したユーザーのID (外部キー)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), comment="投稿者ID")
    # 投稿のテキスト本文
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="投稿の本文")
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
    # Usersテーブルへのリレーション
    user: Mapped["Users"] = relationship("Users", back_populates="posts")
    # この投稿に紐づく「いいね」 (一対多)
    likes: Mapped[List["Likes"]] = relationship(
        "Likes", back_populates="post", cascade="all, delete-orphan"
    )
    # この投稿に紐づくタグ (中間テーブル経由)
    post_tags: Mapped[List["PostTags"]] = relationship(
        "PostTags", back_populates="post", cascade="all, delete-orphan"
    )
    # この投稿に紐づく画像 (一対多)
    images: Mapped[List["PostImages"]] = relationship(
        "PostImages", back_populates="post", cascade="all, delete-orphan"
    )
    # この投稿に紐づくコメント (一対多)
    comments: Mapped[List["Comments"]] = relationship(
        "Comments", back_populates="post", cascade="all, delete-orphan"
    )
    # この投稿に紐づくブックマーク (一対多)
    bookmarks: Mapped[List["Bookmarks"]] = relationship(
        "Bookmarks", back_populates="post", cascade="all, delete-orphan"
    )


# PostImagesテーブル: 投稿に紐づく画像を格納する
class PostImages(Base):
    __tablename__ = "post_images"

    # 画像を一意に識別するID (主キー)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="画像ID")
    # 関連する投稿のID (外部キー)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), comment="投稿ID")
    # 画像ファイルのURL
    image_url: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="画像URL"
    )
    # 複数画像がある場合の表示順序
    display_order: Mapped[int] = mapped_column(Integer, default=0, comment="表示順")

    # Postsテーブルへのリレーション
    post: Mapped["Posts"] = relationship("Posts", back_populates="images")


# Tagsテーブル: タグのマスタデータを格納する
class Tags(Base):
    __tablename__ = "tags"

    # タグを一意に識別するID (主キー)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="タグID")
    # タグ名 (ユニーク制約)
    name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="タグ名"
    )

    # PostTags中間テーブルへのリレーション
    post_tags: Mapped[List["PostTags"]] = relationship("PostTags", back_populates="tag")


# PostTagsテーブル: 投稿とタグの関連を管理する中間テーブル
class PostTags(Base):
    __tablename__ = "post_tags"
    # 関連する投稿のID (複合主キー、外部キー)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id"), primary_key=True, comment="投稿ID"
    )
    # 関連するタグのID (複合主キー、外部キー)
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id"), primary_key=True, comment="タグID"
    )

    # Postsテーブルへのリレーション
    post: Mapped["Posts"] = relationship("Posts", back_populates="post_tags")
    # Tagsテーブルへのリレーション
    tag: Mapped["Tags"] = relationship("Tags", back_populates="post_tags")


# Likesテーブル: 投稿への「いいね」を記録する
class Likes(Base):
    __tablename__ = "likes"
    # 「いいね」したユーザーのID (複合主キー、外部キー)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True, comment="いいねしたユーザーID"
    )
    # 「いいね」された投稿のID (複合主キー、外部キー)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id"), primary_key=True, comment="いいねされた投稿ID"
    )
    # レコード作成日時 (自動設定)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    # Usersテーブルへのリレーション
    user: Mapped["Users"] = relationship("Users", back_populates="likes")
    # Postsテーブルへのリレーション
    post: Mapped["Posts"] = relationship("Posts", back_populates="likes")


# Followsテーブル: ユーザー間のフォロー関係を記録する
class Follows(Base):
    __tablename__ = "follows"
    # フォローした側のユーザーID (複合主キー、外部キー)
    follower_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True, comment="フォローしたユーザーID"
    )
    # フォローされた側のユーザーID (複合主キー、外部キー)
    following_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True, comment="フォローされたユーザーID"
    )
    # レコード作成日時 (自動設定)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    # フォローしたユーザーへのリレーション (自己参照)
    follower: Mapped["Users"] = relationship(
        "Users", foreign_keys=[follower_id], back_populates="following"
    )
    # フォローされたユーザーへのリレーション (自己参照)
    following: Mapped["Users"] = relationship(
        "Users", foreign_keys=[following_id], back_populates="followers"
    )


# Commentsテーブル: 投稿へのコメントを格納する
class Comments(Base):
    __tablename__ = "comments"
    # コメントを一意に識別するID (主キー)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="コメントID")
    # コメント対象の投稿ID (外部キー)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), comment="投稿ID")
    # コメントしたユーザーのID (外部キー)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), comment="コメントしたユーザーID"
    )
    # コメントのテキスト本文
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="コメント内容")
    # レコード作成日時 (自動設定)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )
    # レコード更新日時 (自動更新)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新日時"
    )

    # Postsテーブルへのリレーション
    post: Mapped["Posts"] = relationship("Posts", back_populates="comments")
    # Usersテーブルへのリレーション
    user: Mapped["Users"] = relationship("Users", back_populates="comments")


# Bookmarksテーブル: 投稿のブックマークを記録する
class Bookmarks(Base):
    __tablename__ = "bookmarks"
    # ブックマークしたユーザーのID (複合主キー、外部キー)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), primary_key=True, comment="ブックマークしたユーザーID"
    )
    # ブックマークされた投稿のID (複合主キー、外部キー)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id"), primary_key=True, comment="ブックマークされた投稿ID"
    )
    # レコード作成日時 (自動設定)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    # Usersテーブルへのリレーション
    user: Mapped["Users"] = relationship("Users", back_populates="bookmarks")
    # Postsテーブルへのリレーション
    post: Mapped["Posts"] = relationship("Posts", back_populates="bookmarks")


# Notificationsテーブル: ユーザーへの通知を格納する
class Notifications(Base):
    __tablename__ = "notifications"
    # 通知を一意に識別するID (主キー)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="通知ID")
    # 通知を受け取るユーザーのID (外部キー)
    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), comment="受信者ID"
    )
    # 通知を発生させたアクションの主体となるユーザーのID (外部キー、NULL許容)
    sender_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), comment="送信者ID"
    )
    # 通知の種類 (例: 'like', 'comment', 'follow')
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="通知タイプ (like, comment, follow)"
    )
    # 通知に関連するオブジェクトのID (例: いいねされた投稿のID)
    target_id: Mapped[Optional[int]] = mapped_column(
        Integer, comment="対象ID (post_id, user_idなど)"
    )
    # ユーザーが通知を読んだかどうか (True: 既読, False: 未読)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, comment="既読フラグ")
    # レコード作成日時 (自動設定)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    # 通知受信者(Users)へのリレーション
    recipient: Mapped["Users"] = relationship(
        "Users",
        foreign_keys=[recipient_user_id],
        back_populates="notifications_received",
    )


# Questionnairesテーブル: アンケートのマスタデータを格納する
class Questionnaires(Base):
    __tablename__ = "questionnaires"
    # アンケートを一意に識別するID (主キー)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="アンケートID")
    # アンケートのタイトル
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="タイトル")
    # アンケートの詳細な説明
    description: Mapped[Optional[str]] = mapped_column(Text, comment="説明")
    # 回答者に付与される報酬ポイント
    points_reward: Mapped[int] = mapped_column(
        Integer, default=0, comment="報酬ポイント"
    )
    # アンケートの回答締切日時
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="締切日時")
    # レコード作成日時 (自動設定)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="作成日時"
    )

    # このアンケートへの回答へのリレーション
    answers: Mapped[List["UserQuestionnaireAnswers"]] = relationship(
        "UserQuestionnaireAnswers", back_populates="questionnaire"
    )


# UserQuestionnaireAnswersテーブル: ユーザーのアンケート回答状況を記録する
class UserQuestionnaireAnswers(Base):
    __tablename__ = "user_questionnaire_answers"
    # 回答レコードを一意に識別するID (主キー)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="回答ID")
    # 回答したユーザーのID (外部キー)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), comment="回答者ID")
    # 回答したアンケートのID (外部キー)
    questionnaire_id: Mapped[int] = mapped_column(
        ForeignKey("questionnaires.id"), comment="アンケートID"
    )
    # 回答した日時 (自動設定)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="回答日時"
    )

    # ユーザーは各アンケートに1度しか回答できないように複合ユニーク制約を定義
    __table_args__ = (PrimaryKeyConstraint("user_id", "questionnaire_id"),)

    # Usersテーブルへのリレーション
    user: Mapped["Users"] = relationship(
        "Users", back_populates="questionnaire_answers"
    )
    # Questionnairesテーブルへのリレーション
    questionnaire: Mapped["Questionnaires"] = relationship(
        "Questionnaires", back_populates="answers"
    )
