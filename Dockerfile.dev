# 1. ベースイメージの指定 (Python 3.12 の軽量版)
FROM python:3.12-slim

# 2. 開発に必要となる可能性のあるツールをインストール (gitは必須)
RUN apt-get update && apt-get install -y git curl

# pip自体を最新版にアップグレードするコマンドを追加
# --no-cache-dir はイメージサイズを小さく保つためのベストプラクティス
RUN pip install --no-cache-dir --upgrade pip

# 3. 作業ディレクトリの作成と指定
WORKDIR /app

# 4. 依存関係ファイルの先行コピー (キャッシュ効率化のため)
# この時点ではrequirements.txtは存在しないが、後のために記述しておく
COPY requirements.txt ./

# 5. 依存関係のインストール
RUN pip install --no-cache-dir -r requirements.txt

# 6. プロジェクト全体のソースコードをコピー
COPY . .

# 7. FastAPIが使用するポートを公開
EXPOSE 8000

# 8. コンテナ起動時のデフォルトコマンド (コメントアウト)
# Dev Containersでは postAttachCommand や手動実行を推奨するため、CMDは不要
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]