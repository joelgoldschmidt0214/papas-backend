# papas-backend

このプロジェクトは、PAPA'sアプリケーションのバックエンドAPIです。FastAPIを使用して構築されています。

## 開発環境のセットアップ

このプロジェクトは開発コンテナー (Dev Containers) を使用して、チーム全員が統一された環境で開発を行います。

### 前提条件

*   [Docker Desktop](https://www.docker.com/products/docker-desktop/)
*   [Visual Studio Code](https://code.visualstudio.com/)
*   VS Code拡張機能: [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### セットアップ手順

1.  このリポジトリをクローンします。
    ```bash
    git clone git@github.com:your-org/papas-backend.git
    ```

2.  クローンしたフォルダをVS Codeで開きます。
    ```bash
    cd papas-backend
    code .
    ```

3.  VS Codeの右下に表示される「**Reopen in Container**」ボタンをクリックします。

以上です！

コンテナのビルドが完了すると、依存関係のインストールと開発サーバーの起動が自動的に行われます。
ブラウザで `http://localhost:8000` にアクセスすると、APIの動作を確認できます。
