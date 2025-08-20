from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from passlib.context import CryptContext

from connect_MySQL import engine

# mymodels_MySQL.pyで定義された全てのモデル（テーブル定義）をインポート
from mymodels_MySQL import (
    Base,
    USERS,
    POSTS,
    TAGS,
    LIKES,
    FOLLOWS,
    POST_TAGS,
    SOCIAL_LOGINS,
    POST_IMAGES,
    COMMENTS,
    BOOKMARKS,
    NOTIFICATIONS,
    SURVEYS,
    SURVEY_RESPONSES,
)

# パスワードのハッシュ化に使用するコンテキストを設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    平文のパスワードを受け取り、bcryptでハッシュ化します。
    """
    return pwd_context.hash(password)


def init_db():
    """
    データベース内にテーブルが存在するかを確認し、存在しない場合のみ全てのテーブルを作成します。
    """
    print("Checking database for tables...")
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        print("Tables not found. Creating all tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
    else:
        print("Tables already exist.")


def insert_sample_data():
    """
    開発やテスト用のサンプルデータをデータベースに投入します。
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        if session.query(USERS).first():
            print("Sample data already exists. Skipping insertion.")
            return

        print("Inserting sample data...")

        # --- サンプルユーザーの作成 ---
        user1 = USERS(
            username="pattyo_tokyogas",
            display_name="パッチョ",
            email="pattyo@example.com",
            password_hash=get_password_hash("password123"),
            bio="東京ガスのパッチョです！",
            area="東京都",
            user_type="tokyogas_member",
            tokyo_gas_customer_id="123456789",
        )
        user2 = USERS(
            username="general_user",
            display_name="一般ユーザーA",
            email="user.a@example.com",
            password_hash=get_password_hash("password456"),
            bio="こんにちは。よろしくお願いします。",
            area="神奈川県",
            user_type="general",
        )
        # ソーシャルログイン用のユーザー (パスワードなし)
        user3_google = USERS(
            username="charlie_g",
            display_name="Charlie Google",
            email="charlie.g@example.com",
        )

        session.add_all([user1, user2, user3_google])
        session.commit()

        # --- SOCIAL_LOGINS テーブルにデータを追加 ---
        social_login_g = SOCIAL_LOGINS(
            user_id=user3_google.user_id,
            provider="Google",
            provider_id="109876543210987654321",
        )
        session.add(social_login_g)
        session.commit()

        # --- サンプル投稿の作成 ---
        post1 = POSTS(
            user_id=user1.user_id, content="今日のガス展、楽しかった！ #東京ガス"
        )
        post2 = POSTS(user_id=user2.user_id, content="新しいレシピに挑戦しました。")
        post3 = POSTS(
            user_id=user3_google.user_id, content="Googleログインで簡単投稿！"
        )
        session.add_all([post1, post2, post3])
        session.commit()

        # --- サンプルタグのマスタデータ作成 ---
        tag_facility = TAGS(tag_name="#おすすめ施設情報")
        tag_deals = TAGS(tag_name="#お得情報")
        tag_gourmet = TAGS(tag_name="#グルメ")
        tag_parenting = TAGS(tag_name="#子育て")
        tag_event = TAGS(tag_name="#イベント")
        tag_eco = TAGS(tag_name="#デコ活")

        session.add_all(
            [
                tag_facility,
                tag_deals,
                tag_gourmet,
                tag_parenting,
                tag_event,
                tag_eco,
            ]
        )
        session.commit()

        # --- 中間テーブルや関連テーブルへのデータ挿入 ---
        like1 = LIKES(user_id=user2.user_id, post_id=post1.post_id)
        follow1 = FOLLOWS(follower_id=user1.user_id, following_id=user2.user_id)
        comment1 = COMMENTS(
            user_id=user2.user_id,
            post_id=post1.post_id,
            content="私も行きたかったです！",
        )
        bookmark1 = BOOKMARKS(user_id=user1.user_id, post_id=post2.post_id)

        # 新しいタグをサンプル投稿に関連付け
        # post1「今日のガス展、楽しかった！」に「#イベント」と「#おすすめ施設情報」を紐付け
        pt_event_1 = POST_TAGS(post_id=post1.post_id, tag_id=tag_event.tag_id)
        pt_facility_1 = POST_TAGS(post_id=post1.post_id, tag_id=tag_facility.tag_id)

        # post2「新しいレシピに挑戦しました。」に「#グルメ」を紐付け
        pt_gourmet_2 = POST_TAGS(post_id=post2.post_id, tag_id=tag_gourmet.tag_id)

        session.add_all(
            [
                like1,
                follow1,
                comment1,
                bookmark1,
                pt_event_1,
                pt_facility_1,
                pt_gourmet_2,
            ]
        )

        session.commit()

        # --- アンケートと回答のサンプルデータ作成 ---
        survey1 = SURVEYS(
            title="アプリの使いやすさについて",
            question_text="このアプリの全体的なデザインや操作感について、あなたの印象に近いものを選択してください。",
            points=50,
            target_audience="all",
        )
        session.add(survey1)
        session.commit()

        response1 = SURVEY_RESPONSES(
            user_id=user1.user_id,
            survey_id=survey1.survey_id,
            choice="very_good",
            comment="とても満足しています！",
        )
        session.add(response1)
        session.commit()

        print("Sample data inserted successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    print("--- Start: Resetting database ---")
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")
    init_db()
    insert_sample_data()
    print("--- Finish: Database has been reset successfully. ---")
