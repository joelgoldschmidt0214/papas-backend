# --- START OF FILE create_tables_MySQL.py ---

from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect, text
from passlib.context import CryptContext
import random

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
    TAGS,  # --- ▼▼▼ 修正点: TAGSをインポート ▼▼▼ ---
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
    各投稿に対して100～200件のいいねを設定します。
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        if session.query(USERS).first():
            print("Sample data already exists. Skipping insertion.")
            return

        print("Inserting sample data...")

        # --- 1. サンプルユーザーの作成 (9名) ---
        common_password = get_password_hash("password123")

        main_users_data = [
            {
                "username": "keiju",
                "display_name": "けいじゅ",
                "email": "user1@example.com",
                "bio": "",
                "area": "",
                "profile_image_url": "/images/user_01.png",
            },
            {
                "username": "hasechu",
                "display_name": "はせちゅー",
                "email": "user2@example.com",
                "bio": "",
                "area": "",
                "profile_image_url": "/images/user_02.png",
            },
            {
                "username": "kenchan",
                "display_name": "けんちゃん",
                "email": "user3@example.com",
                "bio": "",
                "area": "",
                "profile_image_url": "/images/user_03.png",
            },
            {
                "username": "eto",
                "display_name": "えとー",
                "email": "user4@example.com",
                "bio": "",
                "area": "",
                "profile_image_url": "/images/user_04.png",
            },
            {
                "username": "pattyo_official",
                "display_name": "パッチョ（公式）",
                "email": "pattyo.official@example.com",
                "bio": "東京ガスの公式アカウントです。暮らしに役立つ情報やお得なキャンペーンをお知らせします！",
                "area": "東京都",
                "user_type": "tokyogas_member",
                "tokyo_gas_customer_id": "987654321",
            },
            {
                "username": "koto_papa",
                "display_name": "江東区のパパ",
                "email": "koto.papa@example.com",
                "bio": "3歳と5歳の子供の父親です。週末はもっぱら公園巡り。江東区の情報を中心に交換したいです！",
                "area": "東京都江東区",
                "profile_image_url": "",
            },
            {
                "username": "minato_mama",
                "display_name": "港区のママ",
                "email": "minato.mama@example.com",
                "bio": "港区在住、2児の母。子連れで行ける美味しいお店を探しています。",
                "area": "東京都港区",
            },
            {
                "username": "taito_father",
                "display_name": "台東区の父",
                "email": "taito.father@example.com",
                "bio": "下町大好き！台東区のイベント情報があれば教えてください。",
                "area": "東京都台東区",
                "profile_image_url": "",
            },
            {
                "username": "koto_mama_2",
                "display_name": "こうとうママ",
                "email": "koto.mama2@example.com",
                "bio": "最近江東区に引っ越してきました。ご近所付き合いなど、よろしくお願いします。",
                "area": "東京都江東区",
            },
        ]

        main_users = []
        for user_data in main_users_data:
            user = USERS(
                username=user_data["username"],
                display_name=user_data["display_name"],
                email=user_data["email"],
                password_hash=common_password,
                bio=user_data["bio"],
                area=user_data["area"],
                profile_image_url=user_data.get("profile_image_url", ""),
                user_type=user_data.get("user_type", "general"),
                tokyo_gas_customer_id=user_data.get("tokyo_gas_customer_id", None),
            )
            main_users.append(user)

        session.add_all(main_users)
        session.commit()

        # --- 1.5. 大量のダミーユーザーを作成 (200名) ---
        print("Creating 200 dummy users for likes data...")
        dummy_users = []
        for i in range(1, 201):
            dummy_user = USERS(
                username=f"dummy_user_{i:03d}",
                display_name=f"ダミーユーザー{i}",
                email=f"dummy{i}@example.com",
                password_hash=common_password,
                bio=f"テスト用ユーザー{i}です",
                area="東京都",
                profile_image_url=f"/images/user_{i % 4 + 1}.png",
            )
            dummy_users.append(dummy_user)

        session.add_all(dummy_users)
        session.commit()

        all_users = session.query(USERS).all()
        print(f"Total users created: {len(all_users)}")

        # --- ▼▼▼ 修正点: サンプルタグを作成 ▼▼▼ ---
        print("Creating sample tags...")
        tag_names = [
            "イベント",
            "グルメ",
            "子育て",
            "お得情報",
            "公園",
            "カフェ",
            "東京ガス",
            "節約術",
            "地域情報",
            "DIY",
            "お知らせ",
        ]
        tags_map = {name: TAGS(tag_name=name) for name in tag_names}
        session.add_all(tags_map.values())
        session.commit()
        print(f"Created {len(tags_map)} tags.")

        # --- 2. サンプル投稿の作成 (タグ付けあり) ---
        main_users_from_db = (
            session.query(USERS)
            .filter(USERS.username.in_([user["username"] for user in main_users_data]))
            .all()
        )
        user_map = {user.username: user for user in main_users_from_db}

        posts_data = [
            # フォローカテゴリ
            POSTS(
                user_id=user_map["pattyo_official"].user_id,
                content="【お知らせ】夏のガス展を開催します！最新のガス機器に触れるチャンスです。詳細はWebをチェック！",
                is_event_category=True,
                is_follow_category=True,
                tags=[tags_map["イベント"], tags_map["東京ガス"], tags_map["お知らせ"]],
            ),
            POSTS(
                user_id=user_map["pattyo_official"].user_id,
                content="エアコンの温度設定を1℃見直すだけで、大きな節電に繋がります。皆でエコな夏を過ごしましょう！",
                is_follow_category=True,
                tags=[tags_map["節約術"], tags_map["東京ガス"]],
            ),
            POSTS(
                user_id=user_map["pattyo_official"].user_id,
                content="【節電キャンペーン】今月のガス使用量を前年比10%削減すると、ポイントが2倍になります！",
                is_follow_category=True,
                is_otokuinfo_category=True,
                tags=[tags_map["お得情報"], tags_map["節約術"]],
            ),
            POSTS(
                user_id=user_map["pattyo_official"].user_id,
                content="【メンテナンス情報】来週、江東区エリアでガス管の点検作業を行います。ご不便をおかけしますが、ご協力をお願いします。",
                is_follow_category=True,
                tags=[tags_map["地域情報"], tags_map["お知らせ"]],
            ),
            # ご近所さんカテゴリ
            POSTS(
                user_id=user_map["keiju"].user_id,
                content="豊洲公園の新しい遊具、子供が大喜びでした！週末は混みそうですね。",
                is_neighborhood_category=True,
                tags=[tags_map["公園"], tags_map["子育て"], tags_map["地域情報"]],
            ),
            POSTS(
                user_id=user_map["eto"].user_id,
                content="今週末、木場の公園で地域のフリーマーケットがあるみたいですよ！掘り出し物あるかな？",
                is_event_category=True,
                is_neighborhood_category=True,
                tags=[tags_map["イベント"], tags_map["公園"]],
            ),
            POSTS(
                user_id=user_map["eto"].user_id,
                content="門前仲町のパン屋さん、塩パンが最高に美味しいのでおすすめです。",
                is_neighborhood_category=True,
                is_gourmet_category=True,
                tags=[tags_map["グルメ"], tags_map["カフェ"]],
            ),
            POSTS(
                user_id=user_map["keiju"].user_id,
                content="東陽町の図書館、絵本コーナーが広くて子供も飽きずに過ごせます。",
                is_neighborhood_category=True,
                tags=[tags_map["子育て"], tags_map["地域情報"]],
            ),
            POSTS(
                user_id=user_map["kenchan"].user_id,
                content="江東区の地域イベント、参加してみたいのですが、どこで情報を集めていますか？",
                is_neighborhood_category=True,
                tags=[tags_map["イベント"], tags_map["地域情報"]],
            ),
            # イベントカテゴリ
            POSTS(
                user_id=user_map["kenchan"].user_id,
                content="上野の森美術館でやっている恐竜展、迫力満点でした。夏休みの思い出にぜひ。",
                is_event_category=True,
                tags=[tags_map["イベント"], tags_map["子育て"]],
            ),
            POSTS(
                user_id=user_map["hasechu"].user_id,
                content="麻布十番のお祭り、すごい人でした！屋台の焼きそばが美味しかった〜。",
                is_event_category=True,
                is_gourmet_category=True,
                tags=[tags_map["イベント"], tags_map["グルメ"]],
            ),
            # グルメカテゴリ
            POSTS(
                user_id=user_map["hasechu"].user_id,
                content="芝公園近くのイタリアン、テラス席が気持ちよくて子連れでも安心でした。ピザが絶品！",
                is_gourmet_category=True,
                tags=[tags_map["グルメ"], tags_map["子育て"]],
            ),
            POSTS(
                user_id=user_map["keiju"].user_id,
                content="有明ガーデンのフードコート、お店が充実していて家族みんなで楽しめますね。",
                is_gourmet_category=True,
                tags=[tags_map["グルメ"], tags_map["子育て"]],
            ),
            # 子育てカテゴリ
            POSTS(
                user_id=user_map["keiju"].user_id,
                content="江東区の子育て支援センター、スタッフの方々がとても親切で助かっています。",
                is_neighborhood_category=True,
                is_kosodate_category=True,
                tags=[tags_map["子育て"], tags_map["地域情報"]],
            ),
            POSTS(
                user_id=user_map["kenchan"].user_id,
                content="子連れで行ける映画館、音響が調整されていて子供も安心して観られます。週末の過ごし方に困った時におすすめです。",
                is_kosodate_category=True,
                tags=[tags_map["子育て"], tags_map["イベント"]],
            ),
            # お得情報カテゴリ
            POSTS(
                user_id=user_map["eto"].user_id,
                content="【節約術】スーパーの閉店間際、生鮮食品が半額になることが多いです。夕方の買い物がお得ですよ。",
                is_otokuinfo_category=True,
                tags=[tags_map["お得情報"], tags_map["節約術"]],
            ),
            # デコ活カテゴリ（DIY）
            POSTS(
                user_id=user_map["hasechu"].user_id,
                content="【DIY】子供の部屋の壁紙、手作りで可愛くデコレーションしました！材料費も安く済んで満足です。",
                is_decokatsu_category=True,
                tags=[tags_map["DIY"], tags_map["子育て"]],
            ),
            POSTS(
                user_id=user_map["eto"].user_id,
                content="【DIY】ベランダのガーデニング、ハーブを育てて料理に使っています。フレッシュな香りが最高です。",
                is_decokatsu_category=True,
                tags=[tags_map["DIY"], tags_map["グルメ"]],
            ),
        ]

        session.add_all(posts_data)
        session.commit()

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
        session.commit()

        # --- 4. 大量のいいねデータを作成 ---
        print("Creating likes data (100-200 likes per post)...")
        likes_data = []
        all_posts_from_db = session.query(POSTS).all()  # 投稿IDを確実に取得

        for post in all_posts_from_db:
            likes_count = random.randint(100, 200)
            selected_users = random.sample(all_users, likes_count)
            for user in selected_users:
                likes_data.append(LIKES(user_id=user.user_id, post_id=post.post_id))

        batch_size = 1000
        for i in range(0, len(likes_data), batch_size):
            batch = likes_data[i : i + batch_size]
            session.add_all(batch)
            session.commit()
            print(
                f"Added likes batch {i // batch_size + 1}/{(len(likes_data) + batch_size - 1) // batch_size}"
            )

        # --- 5. その他の関連データの作成 ---
        post_map = {p.content: p for p in all_posts_from_db}

        related_data = [
            COMMENTS(
                user_id=user_map["eto"].user_id,
                post_id=post_map[
                    "【お知らせ】夏のガス展を開催します！最新のガス機器に触れるチャンスです。詳細はWebをチェック！"
                ].post_id,
                content="情報ありがとうございます！明日さっそく行ってみます！",
            ),
            COMMENTS(
                user_id=user_map["keiju"].user_id,
                post_id=post_map[
                    "今週末、木場の公園で地域のフリーマーケットがあるみたいですよ！掘り出し物あるかな？"
                ].post_id,
                content="フリマ情報助かります！",
            ),
            FOLLOWS(
                follower_id=user_map["keiju"].user_id,
                following_id=user_map["koto_mama_2"].user_id,
            ),
            FOLLOWS(
                follower_id=user_map["koto_mama_2"].user_id,
                following_id=user_map["keiju"].user_id,
            ),
            FOLLOWS(
                follower_id=user_map["keiju"].user_id,
                following_id=user_map["pattyo_official"].user_id,
            ),
            FOLLOWS(
                follower_id=user_map["hasechu"].user_id,
                following_id=user_map["pattyo_official"].user_id,
            ),
            BOOKMARKS(
                user_id=user_map["keiju"].user_id,
                post_id=post_map[
                    "今週末、木場の公園で地域のフリーマーケットがあるみたいですよ！掘り出し物あるかな？"
                ].post_id,
            ),
            BOOKMARKS(
                user_id=user_map["hasechu"].user_id,
                post_id=post_map[
                    "門前仲町のパン屋さん、塩パンが最高に美味しいのでおすすめです。"
                ].post_id,
            ),
            SURVEY_RESPONSES(
                user_id=user_map["keiju"].user_id,
                survey_id=survey1.survey_id,
                choice="agree",
                comment="アスレチック的な遊具が欲しいです。",
            ),
            SURVEY_RESPONSES(
                user_id=user_map["koto_mama_2"].user_id,
                survey_id=survey1.survey_id,
                choice="agree",
                comment="小さい子向けの安全な砂場が充実すると嬉しい。",
            ),
            SURVEY_RESPONSES(
                user_id=user_map["hasechu"].user_id,
                survey_id=survey2.survey_id,
                choice="disagree",
                comment="安全性の説明が不十分だと感じます。",
            ),
        ]
        session.add_all(related_data)
        session.commit()

        print("Sample data inserted successfully!")
        print(f"Created {len(all_users)} users")
        print(f"Created {len(all_posts_from_db)} posts with tags")
        print(f"Created {len(likes_data)} likes")

    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    print("--- Start: Resetting database ---")
    print("Dropping all tables defined in models...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")

    init_db()
    insert_sample_data()
    print("--- Finish: Database has been reset successfully. ---")
