# 1. ベースイメージの指定 (Python 3.12 の軽量版)
FROM python:3.12-slim

# 2. 作業ディレクトリの作成と指定
WORKDIR /app

# 3. 依存関係ファイルの先行コピー
COPY requirements.txt ./

# 4. 依存関係のインストール
# --no-cache-dir はイメージサイズを小さく保つためのベストプラクティス
RUN pip install --no-cache-dir -r requirements.txt

# 5. アプリケーションコードをコピー
# ここでは ./app のようにアプリのコードがあるディレクトリだけをコピーするのがより望ましいですが、
# './' でも動作します。
COPY . .

# 6. FastAPIが使用するポートを公開
EXPOSE 8000

# 7. コンテナ起動時のデフォルトコマンド
# ここが最重要！コンテナ起動時にUvicornサーバーを自動で起動する
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]