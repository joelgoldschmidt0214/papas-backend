# --- START OF FILE create_tables_MySQL.py ---

from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect, text
from passlib.context import CryptContext

from connect_MySQL import engine

# mymodels_MySQL.pyで定義された全てのモデル（テーブル定義）をインポート
from mymodels_MySQL import (
    Base,
    USERS,
    POSTS,
    LIKES,
    FOLLOWS,
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

        # --- 1. サンプルユーザーの作成 (5名) ---
        common_password = get_password_hash("password123")

        user1 = USERS(
            username="keiju",
            display_name="けいじゅ",
            email="",
            password_hash=common_password,
            bio="",
            area="",
            profile_image_url="/images/user_01.png",
        )
        user2 = USERS(
            username="hasechu",
            display_name="はせちゅー",
            email="",
            password_hash=common_password,
            bio="",
            area="",
            profile_image_url="/images/user_02.png",
        )
        user3 = USERS(
            username="kenchan",
            display_name="けんちゃん",
            email="",
            password_hash=common_password,
            bio="",
            area="",
            profile_image_url="/images/user_03.png",
        )
        user4 = USERS(
            username="eto",
            display_name="えとー",
            email="",
            password_hash=common_password,
            bio="",
            area="",
            profile_image_url="/images/user_04.png",
        )
        user5 = USERS(
            username="pattyo_official",
            display_name="パッチョ（公式）",
            email="pattyo.official@example.com",
            password_hash=common_password,
            bio="東京ガスの公式アカウントです。暮らしに役立つ情報やお得なキャンペーンをお知らせします！",
            area="東京都",
            user_type="tokyogas_member",
            tokyo_gas_customer_id="987654321",
        )
        user6 = USERS(
            username="koto_papa",
            display_name="江東区のパパ",
            email="koto.papa@example.com",
            password_hash=common_password,
            bio="3歳と5歳の子供の父親です。週末はもっぱら公園巡り。江東区の情報を中心に交換したいです！",
            area="東京都江東区",
            profile_image_url="",
        )
        user7 = USERS(
            username="minato_mama",
            display_name="港区のママ",
            email="minato.mama@example.com",
            password_hash=common_password,
            bio="港区在住、2児の母。子連れで行ける美味しいお店を探しています。",
            area="東京都港区",
        )
        user8 = USERS(
            username="taito_father",
            display_name="台東区の父",
            email="taito.father@example.com",
            password_hash=common_password,
            bio="下町大好き！台東区のイベント情報があれば教えてください。",
            area="東京都台東区",
            profile_image_url="/images/user_02.png",
        )
        user9 = USERS(
            username="koto_mama_2",
            display_name="こうとうママ",
            email="koto.mama2@example.com",
            password_hash=common_password,
            bio="最近江東区に引っ越してきました。ご近所付き合いなど、よろしくお願いします。",
            area="東京都江東区",
        )

        session.add_all([user1, user2, user3, user4, user5, user6, user7, user8, user9])
        session.commit()  # ユーザーIDを確定させるため、ここで一度コミット

        # --- 2. サンプル投稿の作成 (10件) ---
        # ▼▼▼ content内のハッシュタグを削除 ▼▼▼
        posts_data = [
            POSTS(
                user_id=user1.user_id,
                content="豊洲公園の新しい遊具、子供が大喜びでした！週末は混みそうですね。",
                is_neighborhood_category=True,
            ),
            POSTS(
                user_id=user2.user_id,
                content="芝公園近くのイタリアン、テラス席が気持ちよくて子連れでも安心でした。ピザが絶品！",
                is_gourmet_category=True,
            ),
            POSTS(
                user_id=user4.user_id,
                content="今週末、木場の公園で地域のフリーマーケットがあるみたいですよ！掘り出し物あるかな？",
                is_event_category=True,
                is_neighborhood_category=True,
            ),
            POSTS(
                user_id=user3.user_id,
                content="上野の森美術館でやっている恐竜展、迫力満点でした。夏休みの思い出にぜひ。",
                is_event_category=True,
            ),
            POSTS(
                user_id=user1.user_id,
                content="有明ガーデンのフードコート、お店が充実していて家族みんなで楽しめますね。",
                is_gourmet_category=True,
            ),
            POSTS(
                user_id=user5.user_id,
                content="【お知らせ】夏のガス展を開催します！最新のガス機器に触れるチャンスです。詳細はWebをチェック！",
                is_event_category=True,
                is_follow_category=True,
            ),
            POSTS(
                user_id=user2.user_id,
                content="麻布十番のお祭り、すごい人でした！屋台の焼きそばが美味しかった〜。",
                is_event_category=True,
                is_gourmet_category=True,
            ),
            POSTS(
                user_id=user4.user_id,
                content="門前仲町のパン屋さん、塩パンが最高に美味しいのでおすすめです。",
                is_neighborhood_category=True,
                is_gourmet_category=True,
            ),
            POSTS(
                user_id=user1.user_id,
                content="東陽町の図書館、絵本コーナーが広くて子供も飽きずに過ごせます。",
                is_neighborhood_category=True,
            ),
            POSTS(
                user_id=user5.user_id,
                content="エアコンの温度設定を1℃見直すだけで、大きな節電に繋がります。皆でエコな夏を過ごしましょう！",
                is_follow_category=True,
            ),
        ]
        # ▲▲▲ content内のハッシュタグを削除 ▲▲▲
        session.add_all(posts_data)
        session.commit()  # 投稿IDを確定させるため、ここでコミット

        # --- 3. アンケートの作成 (3件) ---
        survey1 = SURVEYS(
            title="（仮）新設公園の遊具に関するアンケート",
            question_text="江東区に新しく作られる公園について、どのような遊具があれば嬉しいですか？",
            points=30,
            target_audience="all",
        )
        survey2 = SURVEYS(
            title="（仮）次世代エネルギー施設に関するご意見募集",
            question_text="近隣エリアへの次世代エネルギー施設（原子力発電を含む）の建設について、あなたの考えをお聞かせください。",
            points=100,
            target_audience="all",
        )
        survey3 = SURVEYS(
            title="家庭での節電に関する意識調査",
            question_text="あなたは普段、家庭での節電を意識していますか？",
            points=20,
            target_audience="tokyogas_member",
        )
        session.add_all([survey1, survey2, survey3])
        session.commit()  # アンケートIDを確定させる

        # --- 4. 関連データの作成 ---
        # いいね、コメント、フォロー、ブックマーク、アンケート回答
        related_data = [
            LIKES(
                user_id=user2.user_id, post_id=posts_data[0].post_id
            ),  # 港区ママが江東区パパの公園投稿にいいね
            LIKES(
                user_id=user4.user_id, post_id=posts_data[0].post_id
            ),  # こうとうママも公園投稿にいいね
            LIKES(
                user_id=user1.user_id, post_id=posts_data[1].post_id
            ),  # 江東区パパが港区ママのグルメ投稿にいいね
            LIKES(
                user_id=user3.user_id, post_id=posts_data[5].post_id
            ),  # 台東区の父が公式のお知らせにいいね
            COMMENTS(
                user_id=user4.user_id,
                post_id=posts_data[0].post_id,
                content="情報ありがとうございます！明日さっそく行ってみます！",
            ),
            COMMENTS(
                user_id=user1.user_id,
                post_id=posts_data[2].post_id,
                content="フリマ情報助かります！",
            ),
            FOLLOWS(
                follower_id=user1.user_id, following_id=user4.user_id
            ),  # 江東区パパがこうとうママをフォロー
            FOLLOWS(
                follower_id=user4.user_id, following_id=user1.user_id
            ),  # こうとうママが江東区パパをフォロー
            FOLLOWS(
                follower_id=user1.user_id, following_id=user5.user_id
            ),  # みんな公式をフォロー
            FOLLOWS(follower_id=user2.user_id, following_id=user5.user_id),
            FOLLOWS(follower_id=user3.user_id, following_id=user5.user_id),
            BOOKMARKS(
                user_id=user1.user_id, post_id=posts_data[2].post_id
            ),  # フリマ情報をブックマーク
            BOOKMARKS(
                user_id=user2.user_id, post_id=posts_data[7].post_id
            ),  # パン屋さん情報をブックマーク
            SURVEY_RESPONSES(
                user_id=user1.user_id,
                survey_id=survey1.survey_id,
                choice="agree",
                comment="アスレチック的な遊具が欲しいです。",
            ),
            SURVEY_RESPONSES(
                user_id=user4.user_id,
                survey_id=survey1.survey_id,
                choice="agree",
                comment="小さい子向けの安全な砂場が充実すると嬉しい。",
            ),
            SURVEY_RESPONSES(
                user_id=user2.user_id,
                survey_id=survey2.survey_id,
                choice="disagree",
                comment="安全性の説明が不十分だと感じます。",
            ),
            SURVEY_RESPONSES(
                user_id=user3.user_id,
                survey_id=survey2.survey_id,
                choice="neutral",
                comment="もっと情報が必要です。",
            ),
            SURVEY_RESPONSES(
                user_id=user5.user_id,
                survey_id=survey3.survey_id,
                choice="very_conscious",
            ),
        ]
        session.add_all(related_data)
        session.commit()

        print("Sample data inserted successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    print("--- Start: Resetting database ---")

    print("Dropping old tables (post_tags, tags) if they exist...")
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("DROP TABLE IF EXISTS post_tags"))
            connection.execute(text("DROP TABLE IF EXISTS tags"))
    print("Old tables dropped successfully.")

    print("Dropping all tables defined in models...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")

    init_db()
    insert_sample_data()
    print("--- Finish: Database has been reset successfully. ---")
