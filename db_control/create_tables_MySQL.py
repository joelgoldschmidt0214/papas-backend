# create_tables_MySQL.py

from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from passlib.context import CryptContext

from connect_MySQL import engine
from mymodels_MySQL import Base, Users, Posts, Tags, Likes, Follows, PostTags

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def init_db():
    print("Checking database for tables...")
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        print("Tables not found. Creating all tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully!")
    else:
        print("Tables already exist.")


def insert_sample_data():
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        if session.query(Users).first():
            print("Sample data already exists. Skipping insertion.")
            return

        print("Inserting sample data...")

        # --- サンプルユーザーの作成 ---
        user1 = Users(
            username="Alice",
            email="alice@example.com",
            password_hash=get_password_hash("password123"),
            auth_provider="email",
        )
        user2 = Users(
            username="Bob",
            email="bob@example.com",
            password_hash=get_password_hash("password456"),
            auth_provider="email",
        )
        user3_google = Users(
            username="Charlie Google",
            email="charlie.g@example.com",
            password_hash=None,
            auth_provider="google",
            provider_id="109876543210987654321",
        )
        user4_apple = Users(
            username="Diana Apple",
            email="diana.a@example.com",
            password_hash=None,
            auth_provider="apple",
            provider_id="001234.a1b2c3d4e5f6.0123",
        )

        session.add_all([user1, user2, user3_google, user4_apple])
        session.commit()

        # --- サンプル投稿の作成 ---
        post1 = Posts(user_id=user1.id, content="SQLAlchemyは面白い！ #Python")
        post2 = Posts(user_id=user2.id, content="今日のランチはパスタでした。")
        post3 = Posts(user_id=user3_google.id, content="Googleログインで投稿テスト！")
        session.add_all([post1, post2, post3])
        session.commit()

        # --- サンプルタグの作成 ---
        tag_py = Tags(name="Python")
        tag_web = Tags(name="WebDev")
        session.add_all([tag_py, tag_web])
        session.commit()

        # --- 中間テーブルへのデータ挿入 ---
        like1 = Likes(user_id=user2.id, post_id=post1.id)
        like2 = Likes(user_id=user4_apple.id, post_id=post1.id)
        follow1 = Follows(follower_id=user1.id, following_id=user3_google.id)
        pt1 = PostTags(post_id=post1.id, tag_id=tag_py.id)
        pt2 = PostTags(post_id=post3.id, tag_id=tag_web.id)

        session.add_all([like1, like2, follow1, pt1, pt2])
        session.commit()
        print("Sample data inserted successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
    insert_sample_data()
