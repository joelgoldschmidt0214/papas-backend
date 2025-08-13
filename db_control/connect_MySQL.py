import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from pathlib import Path

# このファイルの一つ上の階層にある.envファイルを読み込む
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# 環境変数からデータベース接続情報を読み込み
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
SSL_CA_PATH = os.getenv("SSL_CA_PATH")

# データベース接続URLを構築
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    # 本番環境ではFalseを推奨、デバッグ時はTrue
    # SQLAlchemyが実行するSQLクエリをコンソール（またはログ）に出力するかどうかを制御する設定
    # True：SQLAlchemyがデータベースに対して発行するすべてのSQL文が標準出力に表示されます
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"ssl_ca": SSL_CA_PATH},
)

# .envファイルには以下を記述
# DB_USER=your_user
# DB_PASSWORD=your_password
# DB_HOST=your_host.mysql.database.azure.com
# DB_PORT=3306
# DB_NAME=your_database_name
# SSL_CA_PATH=/path/to/DigiCertGlobalRootG2.crt.pem
