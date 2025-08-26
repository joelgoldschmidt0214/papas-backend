# --- START OF FILE create_tables_MySQL.py ---

from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
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
    COMMENTS,
    BOOKMARKS,
    SURVEYS,
    SURVEY_RESPONSES,
    TAGS,
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

        # --- 1. サンプルユーザーの作成 ---
        common_password = get_password_hash("password123")
        main_users_data = [
            {
                "username": "keiju",
                "display_name": "けいじゅ",
                "email": "user1@example.com",
                "area": "東京都江東区",
                "profile_image_url": "/images/user_01.png",
            },
            {
                "username": "hasechu",
                "display_name": "はせちゅー",
                "email": "user2@example.com",
                "area": "東京都港区",
                "profile_image_url": "/images/user_02.png",
            },
            {
                "username": "kenchan",
                "display_name": "けんちゃん",
                "email": "user3@example.com",
                "area": "東京都台東区",
                "profile_image_url": "/images/user_03.png",
            },
            {
                "username": "eto",
                "display_name": "えとー",
                "email": "user4@example.com",
                "area": "東京都江東区",
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
                "bio": "3歳と6歳の子供の父親です。週末はもっぱら公園巡り。江東区の情報を中心に交換したいです！",
                "area": "東京都江東区",
                "profile_image_url": "/images/user_05.png",
            },
            {
                "username": "minato_mama",
                "display_name": "港区のママ",
                "email": "minato.mama@example.com",
                "bio": "港区在住、2児の母。子連れで行ける美味しいお店を探しています。",
                "area": "東京都港区",
                "profile_image_url": "/images/user_06.png",
            },
        ]
        main_users = []
        for user_data in main_users_data:
            user = USERS(
                username=user_data["username"],
                display_name=user_data["display_name"],
                email=user_data["email"],
                password_hash=common_password,
                bio=user_data.get("bio", ""),
                area=user_data.get("area", ""),
                profile_image_url=user_data.get("profile_image_url", ""),
                user_type=user_data.get("user_type", "general"),
                tokyo_gas_customer_id=user_data.get("tokyo_gas_customer_id", None),
            )
            main_users.append(user)
        session.add_all(main_users)
        session.commit()

        # --- 1.5. 大量のダミーユーザーを作成 (いいね用) ---
        print("Creating 200 dummy users for likes data...")
        dummy_users = []
        for i in range(1, 201):
            dummy_users.append(
                USERS(
                    username=f"dummy_user_{i:03d}",
                    display_name=f"ダミーユーザー{i}",
                    email=f"dummy{i}@example.com",
                    password_hash=common_password,
                )
            )
        session.add_all(dummy_users)
        session.commit()

        all_users = session.query(USERS).all()
        print(f"Total users created: {len(all_users)}")

        # --- 2. サンプルタグの作成 ---
        print("Creating sample tags...")
        tag_names = [
            "フォロー",
            "ご近所さん",
            "イベント",
            "グルメ",
            "子育て",
            "お得情報",
            "デコ活",
        ]
        tags_map = {name: TAGS(tag_name=name) for name in tag_names}
        session.add_all(tags_map.values())
        session.commit()
        print(f"Created {len(tags_map)} tags.")

        # --- 3. サンプル投稿の作成 ---
        main_users_from_db = (
            session.query(USERS)
            .filter(USERS.username.in_([u["username"] for u in main_users_data]))
            .all()
        )
        user_map = {user.username: user for user in main_users_from_db}
        general_users = [
            u for u in main_users_from_db if u.username != "pattyo_official"
        ]

        # 各カテゴリの投稿内容リスト
        posts_contents = {
            "フォロー": [
                "【お知らせ】夏のガス展を開催します！最新のガス機器に触れるチャンスです。詳細はWebをチェック！",
                "【節電キャンペーン】今月のガス使用量を前年比5%削減でポイントがもらえる！ご参加お待ちしております。",
                "【ガス機器の安全点検】専門スタッフがご家庭を訪問し、安全点検を実施中です。ご協力をお願いします。",
                # "【省エネレシピ】ガスコンロの上手な使い方で、調理時間もガス代も節約！今晩のおかずにいかがですか？",
                # "東京ガスの新サービス「〇〇」が始まりました！あなたの暮らしをもっと快適に。",
                # "【災害時の備え】万が一の地震に備えて。ガスメーターの復帰方法をご確認ください。",
                # "エアコンの温度設定を1℃見直すだけで、大きな節電に繋がります。皆でエコな夏を過ごしましょう！",
                # "【メンテナンス情報】来週、一部エリアでガス管の定期メンテナンスを行います。詳細は個別にご連絡いたします。",
                # "Web会員サービス「myTOKYOGAS」で毎月のガス・電気料金を簡単にチェック！ペーパーレスで環境にも優しい。",
                # "「パッチョポイント」を提携ポイントに交換可能！お買い物やマイルに活用できます。",
                # "お風呂の追い焚き機能を上手に使ってガス代を節約するコツをご紹介します。",
                # "最新のガスファンヒーターは、立ち上がりが早く、お部屋を素早く暖めます。冬の準備にいかがですか？",
                # "料理教室のお知らせ：親子で楽しめるピザ作り体験教室を開催します！",
                # "ガス衣類乾燥機「乾太くん」の導入事例をご紹介。家事の時短に大きく貢献します。",
                # "環境にやさしい次世代エネルギーについて、東京ガスの取り組みをご紹介します。",
            ],
            "ご近所さん": [
                "〇〇公園の桜が満開です！今週末がお花見のチャンスかもしれませんね。",
                "△△商店街の角に新しい八百屋さんができましたね。もう行かれた方いますか？",
                "最近、江東区に引っ越してきました！おすすめのスーパーや病院があれば教えてください。",
                # "家の近くで迷子の猫を保護しました。お心当たりのある方はご連絡ください。",
                # "この辺りで評判の良い歯医者さんを探しています。情報お持ちの方、お願いします！",
                # "回覧板で地域の清掃活動のお知らせがありました。今度の日曜日の朝9時からです。",
                # "豊洲の図書館、新しい本がたくさん入っていましたよ。子供向けの絵本も充実しています。",
                # "深夜に犬の鳴き声が聞こえることがあるのですが、うちだけでしょうか？",
                # "〇〇小学校の運動会、今年は一般観覧もできるみたいですね！",
                # "不要になった子供服があります。サイズは90-100cmです。どなたか必要な方いらっしゃいますか？",
                # "この辺はカラスが多いですね。ゴミ出しの時に何か対策されていますか？",
                # "美味しいパン屋さんを探しています。特にハード系のパンが好きなのですが、おすすめはありますか？",
                # "週末に車を停められるコインパーキングで、安いところをご存じないですか？",
                # "子供の自転車の練習ができる、安全な公園を探しています。",
                # "ご近所の方と気軽に話せるようなコミュニティやサークルなど、何かありますか？",
            ],
            "イベント": [
                "今週末、木場の公園でフリーマーケットがあるみたいですよ！掘り出し物あるかな？",
                "富岡八幡宮のお祭り、すごい人でした！屋台の焼きそばが美味しかったです。",
                "区民センターで親子で参加できるプログラミング教室があるそうです。夏休みの自由研究にいいかも。",
                # "隅田川の花火大会、今年こそはいい場所で見たい！穴場スポット知っている方いませんか？",
                # "地域の防災訓練が来月開催されます。いざという時のために参加しましょう！",
                # "ハロウィンイベントで、子供たちがお菓子をもらいに回る企画を計画中です。参加したい方いますか？",
                # "有明ガーデンで大道芸のパフォーマンスをやっていました。無料で楽しめてラッキーでした！",
                # "地元のJAZZフェスティバル、今年も開催決定だそうです！楽しみですね。",
                # "オンラインですが、地域の歴史を学ぶ講演会があるみたいです。面白そう。",
                # "子供向けの職業体験イベント、キッザニア以外で近場で何かご存じですか？",
                # "地元の農家さんが集まるマルシェが、毎月第2日曜日に駅前で開かれています。",
                # "ボランティア募集のお知らせです。地域の子供食堂で配膳のお手伝いをしませんか？",
                # "清澄白河でアートイベントが開催中。ギャラリー巡りが楽しそうです。",
                # "クリスマスの時期に開催される、イルミネーション点灯式の情報です！",
                # "夏休み恒例のラジオ体操、今年は〇〇公園で毎朝6時半からです。",
            ],
            "グルメ": [
                "門前仲町に新しくできたパン屋さん、塩パンが最高に美味しいのでおすすめです。",
                "芝公園近くのイタリアン、テラス席が気持ちよくて子連れでも安心でした。ピザが絶品！",
                "今日のランチは豊洲市場で海鮮丼！新鮮でボリュームもあって大満足でした。",
                # "子連れでも気兼ねなく入れるカフェを探しています。キッズスペースがあるとなお嬉しいです。",
                # "記念日ディナーにおすすめのお店、ありますか？少し奮発しても良いと思っています。",
                # "深夜までやっている美味しいラーメン屋さん、この辺りにありますでしょうか？",
                # "ここのケーキ屋さんのモンブランは絶品です。手土産にも喜ばれますよ。",
                # "最近テイクアウトグルメにハマっています。皆さんのイチオシを教えてください！",
                # "本格的なスパイスカレーが食べられるお店を発見！汗をかきながら食べるのが最高。",
                # "昔ながらの喫茶店で飲むクリームソーダ、なんだか落ち着きます。",
                # "コスパ最強の中華料理屋さん。ランチはいつも行列ができています。",
                # "夏はやっぱりかき氷！ふわふわで頭がキーンとしないお店、知ってますか？",
                # "焼肉が食べたくなったら絶対ここ。お肉の質が違います。",
                # "おしゃれなビアガーデンで、夏の夜風を感じながら飲むビールは格別です。",
                # "ヘルシー志向の方におすすめ！新鮮な野菜がたくさん摂れるデリのお店です。",
            ],
            "子育て": [
                "江東区の子育て支援センター、スタッフの方々がとても親切で助かっています。",
                "子供の習い事、何をさせるか悩みますね。皆さんは何を基準に選んでいますか？",
                "雨の日に子供と遊べる室内施設、レパートリーが尽きてきました...。おすすめありますか？",
                # "不要になったベビーベッドをお譲りします。ご希望の方、ご連絡ください。",
                # "夜間に子供が熱を出してしまって...。この辺りで夜間診療をやっている小児科をご存じないですか？",
                # "予防接種のスケジュール管理、アプリを使っていますか？おすすめがあれば教えてほしいです。",
                # "イヤイヤ期にどう対応していますか？先輩ママさん、アドバイスをお願いします！",
                # "認可保育園の結果が出ましたね。皆さんはどうでしたか？情報交換できれば嬉しいです。",
                # "子供の髪を切るのに、上手で安い美容院を探しています。",
                # "公園デビュー、いつ頃どんな感じでしたか？ちょっと緊張しています。",
                # "アレルギー持ちの子供でも安心して食べられる外食先って、なかなか無いですよね...",
                # "自転車の練習、皆さんどこでやっていますか？交通量の少ない安全な場所を探しています。",
                # "七五三の写真撮影、スタジオの予約はもう済ませましたか？",
                # "小学生の放課後の過ごし方、学童以外で何か選択肢はありますか？",
                # "子供と一緒に楽しめるボードゲームやカードゲームのおすすめを教えてください！",
            ],
            "お得情報": [
                "近所のスーパー、今日まで卵が特売で98円でした！もう売り切れてるかな？",
                "〇〇ドラッグストア、今日はポイント5倍デーですよ！まとめ買いのチャンス。",
                "新しいキャッシュレス決済のキャンペーンで、今なら20%還元されるみたいです。",
                # "区で発行しているプレミアム付き商品券、もう申し込みましたか？かなりお得ですよね。",
                # "ふるさと納税、今年のおすすめ返礼品はこれ！ティッシュペーパーは実用的で助かります。",
                # "携帯キャリアの乗り換えを検討中。学割とか家族割とか、一番お得なのはどこでしょう？",
                # "閉店間際のスーパーは、お惣菜やお刺身が半額になるので狙い目です。",
                # "フリマアプリで子供服を売ったら、ちょっとしたお小遣いになりました。",
                # "電力会社の切り替えをしたら、毎月の電気代が1000円くらい安くなりました！",
                # "飲食店の覆面調査モニター、食事代が浮くし新しいお店も開拓できて一石二鳥です。",
                # "コストコに行くのですが、何かシェアしませんか？量が多くて一人では買いきれないので...",
                # "使わなくなった物を地域の掲示板でお譲りしたら、喜んでもらえて嬉しかったです。",
                # "ネットスーパーの初回限定クーポン、かなり割引率高いので使わないと損ですよ。",
                # "株主優待で届いたカタログギフト、何にしようか迷いますね。",
                # "旅行支援キャンペーン、そろそろ次の情報が出ないか心待ちにしています。",
            ],
            "デコ活": [
                "ベランダの家庭菜園で採れたハーブを使ってエコクッキング。フレッシュな香りが最高です。",
                "着なくなったTシャツをリメイクして、エコバッグを作ってみました！意外と簡単にできますよ。",
                "生ゴミを減らしたくて、コンポストを始めました。土に還るのが楽しみです。",
                # "省エネ性能の高いエアコンに買い替えたら、夏の電気代が目に見えて安くなりました！",
                # "外出時にはマイボトルとマイバッグを必ず持参。少しでもゴミを減らす意識が大切ですね。",
                # "昔ながらの打ち水で、涼しい夏を。クーラーの使用時間も減らせて一石二鳥です。",
                # "プラスチックの使い捨てカトラリーを断る勇気。できることからコツコツと。",
                # "野菜の皮や芯も捨てずに、ベジブロス（野菜だし）を作っています。栄養満点で美味しい！",
                # "子供と一緒に、牛乳パックで椅子を作る工作をしました。エコで楽しい時間でした。",
                # "雨水をためて、ベランダの植物の水やりに使っています。ささやかな節水です。",
                # "環境に配慮した洗剤を選ぶようにしています。少し値段は高いけど、未来への投資ですね。",
                # "自転車通勤に切り替えました。健康的だし、交通費も浮いて、環境にも優しい！",
                # "地域のグリーンカーテンコンテストに応募してみました。ゴーヤがたくさん育っています。",
                # "使わなくなった家具をリペイントして再利用。愛着が湧いて良い感じです。",
                # "節水シャワーヘッドに交換。水圧は変わらないのに、水道代が安くなって驚きました。",
            ],
        }

        posts_data = []
        for tag_name, contents in posts_contents.items():
            for content in contents:
                # 「フォロー」タグはパッチョ公式が投稿
                if tag_name == "フォロー":
                    user = user_map["pattyo_official"]
                else:
                    user = random.choice(general_users)

                # 複数のタグを付けるロジック（例）
                current_tags = [tags_map[tag_name]]
                if "子連れ" in content or "子供" in content:
                    if tags_map["子育て"] not in current_tags:
                        current_tags.append(tags_map["子育て"])
                if "公園" in content:
                    if tags_map["ご近所さん"] not in current_tags:
                        current_tags.append(tags_map["ご近所さん"])
                if "キャンペーン" in content or "節約" in content:
                    if tags_map["お得情報"] not in current_tags:
                        current_tags.append(tags_map["お得情報"])

                post = POSTS(user_id=user.user_id, content=content, tags=current_tags)
                posts_data.append(post)

        session.add_all(posts_data)
        session.commit()
        print(f"Created {len(posts_data)} posts.")

        # --- 4. アンケートの作成 ---
        surveys = [
            SURVEYS(
                title="（仮）新設公園の遊具に関するアンケート",
                question_text="江東区に新しく作られる公園について、どのような遊具があれば嬉しいですか？",
                points=30,
                target_audience="all",
            ),
            SURVEYS(
                title="（仮）次世代エネルギー施設に関するご意見募集",
                question_text="近隣エリアへの次世代エネルギー施設の建設について、あなたの考えをお聞かせください。",
                points=100,
                target_audience="all",
            ),
            SURVEYS(
                title="家庭での節電に関する意識調査",
                question_text="あなたは普段、家庭での節電を意識していますか？",
                points=20,
                target_audience="tokyogas_member",
            ),
        ]
        session.add_all(surveys)
        session.commit()

        # --- 5. 大量のいいねデータを作成 ---
        print("Creating likes data (100-200 likes per post)...")
        likes_data = []
        all_posts_from_db = session.query(POSTS).all()
        for post in all_posts_from_db:
            likes_count = random.randint(100, 200)
            selected_users = random.sample(all_users, likes_count)
            for user in selected_users:
                likes_data.append(LIKES(user_id=user.user_id, post_id=post.post_id))

        # パフォーマンスのためバルクインサート
        session.bulk_save_objects(likes_data)
        session.commit()
        print(f"Created {len(likes_data)} likes.")

        # --- 6. その他の関連データの作成 (コメント、フォローなど) ---
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
                    "今週末、木場の公園でフリーマーケットがあるみたいですよ！掘り出し物あるかな？"
                ].post_id,
                content="フリマ情報助かります！",
            ),
            FOLLOWS(
                follower_id=user_map["keiju"].user_id,
                following_id=user_map["eto"].user_id,
            ),
            FOLLOWS(
                follower_id=user_map["eto"].user_id,
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
                    "今週末、木場の公園でフリーマーケットがあるみたいですよ！掘り出し物あるかな？"
                ].post_id,
            ),
            BOOKMARKS(
                user_id=user_map["hasechu"].user_id,
                post_id=post_map[
                    "門前仲町に新しくできたパン屋さん、塩パンが最高に美味しいのでおすすめです。"
                ].post_id,
            ),
            SURVEY_RESPONSES(
                user_id=user_map["keiju"].user_id,
                survey_id=surveys[0].survey_id,
                choice="agree",
                comment="アスレチック的な遊具が欲しいです。",
            ),
            SURVEY_RESPONSES(
                user_id=user_map["eto"].user_id,
                survey_id=surveys[0].survey_id,
                choice="agree",
                comment="小さい子向けの安全な砂場が充実すると嬉しい。",
            ),
            SURVEY_RESPONSES(
                user_id=user_map["hasechu"].user_id,
                survey_id=surveys[1].survey_id,
                choice="disagree",
                comment="安全性の説明が不十分だと感じます。",
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
    print("Dropping all tables defined in models...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")

    init_db()
    insert_sample_data()
    print("--- Finish: Database has been reset successfully. ---")
