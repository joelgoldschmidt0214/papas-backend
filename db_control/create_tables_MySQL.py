from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from passlib.context import CryptContext

from connect_MySQL import engine

# mymodels_MySQL.pyで定義された全てのモデル（テーブル定義）をインポート
from mymodels_MySQL import (
    Base,
    Users,
    Posts,
    Tags,
    Likes,
    Follows,
    PostTags,
    SocialLogins,
    PostImages,
    Comments,
    Bookmarks,
    Notifications,
    Questionnaires,
    UserQuestionnaireAnswers,
)

# パスワードのハッシュ化に使用するコンテキストを設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    平文のパスワードを受け取り、bcryptでハッシュ化します。

    Args:
        password (str): ハッシュ化する平文のパスワード。

    Returns:
        str: ハッシュ化されたパスワード文字列。
    """
    return pwd_context.hash(password)


def init_db():
    """
    データベース内にテーブルが存在するかを確認し、存在しない場合のみ全てのテーブルを作成します。
    冪等性（何度実行しても同じ結果になること）を保つためのチェックです。
    """
    print("Checking database for tables...")
    # データベースのメタデータを調べるためのinspectorを作成
    inspector = inspect(engine)
    # 代表的なテーブル 'users' が存在するかどうかで、初期化済みかを判断
    if "users" not in inspector.get_table_names():
        print("Tables not found. Creating all tables...")
        # Baseを継承した全てのモデルクラスに対応するテーブルをデータベース内に作成
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
    else:
        print("Tables already exist.")


def insert_sample_data():
    """
    開発やテスト用のサンプルデータをデータベースに投入します。
    既にデータが存在する場合は、重複を避けるため処理をスキップします。
    """
    # データベースセッションを開始
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 既にUsersテーブルにデータがあるか確認し、あれば処理を中断
        if session.query(Users).first():
            print("Sample data already exists. Skipping insertion.")
            return

        print("Inserting sample data...")

        # --- サンプルユーザーの作成 ---
        user1 = Users(
            username="Alice",
            email="alice@example.com",
            password_hash=get_password_hash("password123"),
            bio="はじめまして、アリスです。よろしくお願いします！",
            location="東京",
        )
        user2 = Users(
            username="Bob",
            email="bob@example.com",
            password_hash=get_password_hash("password456"),
            bio="ボブです。趣味はプログラミングです。",
            location="大阪",
        )
        # ソーシャルログイン用のユーザー (パスワードなし)
        user3_google = Users(
            username="Charlie Google",
            email="charlie.g@example.com",
        )
        user4_apple = Users(
            username="Diana Apple",
            email="diana.a@example.com",
        )

        session.add_all([user1, user2, user3_google, user4_apple])
        # 一度コミットしてユーザーIDを確定させ、後続の処理で外部キーとして利用できるようにする
        session.commit()

        # --- SocialLogins テーブルにデータを追加 ---
        social_login_g = SocialLogins(
            user_id=user3_google.id,
            provider="google",
            provider_user_id="109876543210987654321",
        )
        social_login_a = SocialLogins(
            user_id=user4_apple.id,
            provider="apple",
            provider_user_id="001234.a1b2c3d4e5f6.0123",
        )
        session.add_all([social_login_g, social_login_a])
        session.commit()

        # --- サンプル投稿の作成 ---
        post1 = Posts(user_id=user1.id, content="SQLAlchemyは面白い！ #Python")
        post2 = Posts(user_id=user2.id, content="今日のランチはパスタでした。")
        post3 = Posts(user_id=user3_google.id, content="Googleログインで投稿テスト！")
        session.add_all([post1, post2, post3])
        session.commit()

        # --- サンプルタグのマスタデータ作成 ---
        tag_py = Tags(name="Python")
        tag_web = Tags(name="WebDev")
        session.add_all([tag_py, tag_web])
        session.commit()

        # --- 中間テーブル（Likes, Follows, PostTags）や関連テーブルへのデータ挿入 ---
        like1 = Likes(
            user_id=user2.id, post_id=post1.id
        )  # BobがAliceの投稿に「いいね」
        like2 = Likes(
            user_id=user4_apple.id, post_id=post1.id
        )  # DianaがAliceの投稿に「いいね」
        follow1 = Follows(
            follower_id=user1.id, following_id=user3_google.id
        )  # AliceがCharlieをフォロー
        pt1 = PostTags(
            post_id=post1.id, tag_id=tag_py.id
        )  # post1に「Python」タグを紐付け
        pt2 = PostTags(
            post_id=post3.id, tag_id=tag_web.id
        )  # post3に「WebDev」タグを紐付け

        # コメントとブックマークのサンプルデータ
        comment1 = Comments(
            user_id=user2.id, post_id=post1.id, content="本当にそう思います！"
        )  # BobがAliceの投稿にコメント
        bookmark1 = Bookmarks(
            user_id=user1.id, post_id=post2.id
        )  # AliceがBobの投稿をブックマーク

        session.add_all([like1, like2, follow1, pt1, pt2, comment1, bookmark1])
        # 全てのサンプルデータをデータベースに反映
        session.commit()
        print("Sample data inserted successfully!")

    except Exception as e:
        # データ投入中にエラーが発生した場合、変更を全て元に戻す（ロールバック）
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        # 処理が正常に終了してもエラーが発生しても、必ずセッションを閉じる
        session.close()


# このスクリプトが直接実行された場合に、以下の処理を実行します。
# `python create_tables_MySQL.py` のように実行するとここが動きます。
if __name__ == "__main__":
    print("--- Start: Resetting database ---")

    # 処理の流れ:
    # 1. 既存の全テーブルを削除
    # 2. 全てのテーブルを再作成
    # 3. サンプルデータを投入
    # これにより、何度実行しても同じ状態のデータベースが再現されます。

    # 1. 最初に既存のテーブルをすべて削除
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")

    # 2. テーブルを新規作成
    init_db()

    # 3. サンプルデータを挿入
    insert_sample_data()

    print("--- Finish: Database has been reset successfully. ---")
