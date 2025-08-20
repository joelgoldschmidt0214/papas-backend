# Requirements Document

## Introduction

TOMOSU（地域SNSアプリ）のMVPバックエンドAPIシステムを設計・実装します。このAPIは、地域住民の情報交換体験を検証するための最小限の機能を提供し、Azure Container Apps環境でのパフォーマンス最適化を重視した設計とします。認証は簡略化し、投稿データはキャッシュベースで高速動作を実現します。

## Requirements

### Requirement 1: 簡略化ユーザー認証機能（MVP版）

**User Story:** As a 地域住民, I want 簡単にログインしてアプリを体験できる, so that 手軽に地域SNSの機能を試せる

#### Acceptance Criteria

1. WHEN ユーザーがログイン画面を表示する THEN システム SHALL デフォルトのメールアドレスとパスワードを入力欄に表示する
2. WHEN ユーザーがログインボタンを押す THEN システム SHALL 入力内容に関係なく固定のユーザーIDでログイン成功とし、セッション情報をクッキーに保存する
3. WHEN ログイン後のAPIアクセスが発生する THEN システム SHALL 固定ユーザーIDを使用してレスポンスを返す
4. WHEN ユーザーがプロフィール情報を取得する THEN システム SHALL 事前定義された固定ユーザー情報を返す
5. WHEN ユーザーがログアウトする THEN システム SHALL セッションクッキーを削除する

### Requirement 2: キャッシュベース投稿管理機能（MVP版）

**User Story:** As a 地域住民, I want 地域の投稿を高速で閲覧できる, so that ストレスなく地域情報を確認できる

#### Acceptance Criteria

1. WHEN システムが起動する THEN システム SHALL データベースから全投稿データ（約100件）をメモリキャッシュに読み込む
2. WHEN ユーザーが投稿一覧を取得する THEN システム SHALL キャッシュから投稿を新しい順でページネーション付きで返す
3. WHEN ユーザーが特定のタグで投稿を検索する THEN システム SHALL キャッシュからタグでフィルタリングした投稿一覧を返す
4. WHEN ユーザーが新規投稿を作成する THEN システム SHALL 投稿をキャッシュに追加し、データベースには保存しない
5. WHEN 新規投稿がキャッシュに追加される THEN システム SHALL タイムライン上で見かけ上表示されるようにする

### Requirement 3: 基本コメント機能（表示のみ）

**User Story:** As a 地域住民, I want 投稿のコメントを閲覧できる, so that 他の住民の意見を参考にできる

#### Acceptance Criteria

1. WHEN システムが起動する THEN システム SHALL データベースから全コメントデータをキャッシュに読み込む
2. WHEN ユーザーが特定投稿のコメント一覧を取得する THEN システム SHALL キャッシュから該当投稿のコメントを古い順で返す
3. WHEN コメント一覧を返す際 THEN システム SHALL コメント投稿者の基本情報（ユーザー名、表示名）を含める

### Requirement 4: いいね・ブックマーク機能（表示のみ）

**User Story:** As a 地域住民, I want 投稿のいいね数やブックマーク数を確認できる, so that 人気の投稿を把握できる

#### Acceptance Criteria

1. WHEN システムが起動する THEN システム SHALL データベースからいいね・ブックマークデータをキャッシュに読み込む
2. WHEN 投稿一覧を返す際 THEN システム SHALL 各投稿のいいね数とブックマーク数を含める
3. WHEN ユーザーがブックマークした投稿一覧を取得する THEN システム SHALL キャッシュから該当ユーザーのブックマーク投稿を返す

### Requirement 5: フォロー機能（表示のみ）

**User Story:** As a 地域住民, I want フォロー関係を確認できる, so that ユーザー間の繋がりを把握できる

#### Acceptance Criteria

1. WHEN システムが起動する THEN システム SHALL データベースからフォロー関係データをキャッシュに読み込む
2. WHEN ユーザーのフォロワー一覧を取得する THEN システム SHALL キャッシュから該当ユーザーをフォローしているユーザー一覧を返す
3. WHEN ユーザーのフォロー中一覧を取得する THEN システム SHALL キャッシュから該当ユーザーがフォローしているユーザー一覧を返す

### Requirement 6: タグ管理機能（表示のみ）

**User Story:** As a 地域住民, I want タグ別に投稿を閲覧できる, so that 興味のあるカテゴリの情報を効率的に確認できる

#### Acceptance Criteria

1. WHEN システムが起動する THEN システム SHALL データベースからタグ・投稿タグ関連データをキャッシュに読み込む
2. WHEN 投稿一覧を返す際 THEN システム SHALL 各投稿に関連付けられたタグ一覧を含める
3. WHEN タグ一覧を取得する THEN システム SHALL キャッシュから使用されているタグの一覧を返す
4. WHEN 特定タグの投稿を取得する THEN システム SHALL キャッシュからタグでフィルタリングした投稿を返す

### Requirement 7: アンケート機能（表示のみ）

**User Story:** As a 地域住民, I want 地域のアンケートを閲覧できる, so that 地域の課題や関心事を把握できる

#### Acceptance Criteria

1. WHEN システムが起動する THEN システム SHALL データベースからアンケート・回答データをキャッシュに読み込む
2. WHEN ユーザーがアンケート一覧を取得する THEN システム SHALL キャッシュから公開中のアンケート一覧を返す
3. WHEN アンケートの回答結果を取得する THEN システム SHALL キャッシュから集計された回答結果を返す

### Requirement 8: パフォーマンス最適化

**User Story:** As a システム利用者, I want 高速なAPIレスポンスを受けたい, so that ストレスなくアプリを利用できる

#### Acceptance Criteria

1. WHEN システムが起動する THEN システム SHALL 5秒以内に全データをキャッシュに読み込み完了する
2. WHEN APIエンドポイントにリクエストが送信される THEN システム SHALL 95%のリクエストを200ms以内で応答する
3. WHEN キャッシュからデータを取得する際 THEN システム SHALL データベースアクセスを行わない
4. WHEN ページネーションを実装する際 THEN システム SHALL 一度に返すデータ量を適切に制限する

### Requirement 9: エラーハンドリング

**User Story:** As a システム利用者, I want 適切なエラーメッセージを受けたい, so that 問題を理解できる

#### Acceptance Criteria

1. WHEN 無効なリクエストが送信される THEN システム SHALL 適切なHTTPステータスコードとエラーメッセージを返す
2. WHEN 存在しないリソースにアクセスする THEN システム SHALL 404エラーを返す
3. WHEN システム内部エラーが発生する THEN システム SHALL 500エラーを返し、詳細をログに記録する
4. WHEN キャッシュの初期化に失敗する THEN システム SHALL 適切なエラーメッセージでサービス停止する

### Requirement 10: システム監視・ログ

**User Story:** As a システム管理者, I want システムの動作状況を監視したい, so that 問題を早期発見できる

#### Acceptance Criteria

1. WHEN APIリクエストが処理される THEN システム SHALL リクエスト情報をログに記録する
2. WHEN エラーが発生する THEN システム SHALL エラー詳細をログに記録する
3. WHEN システムの健全性チェックが要求される THEN システム SHALL ヘルスチェックエンドポイントで状態を返す
4. WHEN キャッシュの状態確認が要求される THEN システム SHALL キャッシュ統計情報を返す