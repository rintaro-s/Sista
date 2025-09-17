# Sista — 最初の一歩を代行するアシスタント

このリポジトリは、Next.js フロントエンドと FastAPI バックエンド、PostgreSQL を Docker Compose で起動できるフルスタックのサンプル実装です。

# 技術スタック迷走してて使い方グッチャグチャやけどstreamlitとdocker起動したらとりあえずOK♡

目的:
- タスク（最初の一歩）を作成・一覧・更新・削除できるアプリを、DB で永続化して提供します。
- フロントは `sample_design.ts` に沿ったモダンな UI を実装しています。

主な構成:
- frontend/: streamlit
- backend/: FastAPI + SQLModel（Postgres に永続化）
- docker-compose.yml: db/backend/frontend をまとめて起動

クイックスタート（Docker Compose）

1) 必要なツール
- Docker と Docker Compose

2) 起動

```bash
docker compose up --build
```
<!-- 
3) アクセス
- フロントエンド: http://localhost:3000
- バックエンド（API）: http://localhost:8030/tasks -->

開発メモ
- バックエンドの依存は `backend/requirements.txt` にあります。
- フロントはローカルバインドマウントしているため、ソースを編集すると即座に反映されます（pnpm dev を実行）。

次の作業（提案）
- 本番用ビルドやリバースプロキシ設定（nginx）
- マイグレーションツール（alembic 等）の導入
- 認証（ユーザー管理）

以上です。
コンセプト：
「あなたがタスクを先延ばししてる間、Sitstaが『最初の一歩』を代行・誘導・強制（？）してくれる」 

Sistaのキャラ設定：
キャラ：Sっ子な妹
口調：「…あ、それ、今やっといたほうがよくない？」とか「えー、まだやってないの？じゃあ、ダレコがちょっと手伝うね…」
特技：「最初の一歩」を「超・細分化」して、脳死でもできるレベルまで落とす
秘密兵器：「やる気のないあなたに代わって、最初の1アクションを勝手にやっちゃう」機能
核機能：
【最初の一歩自動提案】,
タスク例：「税金の申告をしたい」
ダレコ：「じゃあ、まず『国税庁のHPを開く』からね。…開いた？開いてない？じゃあ、ダレコがリンク送っとくね。」
→ ボタン1つでブラウザ開く。「開く」までが最初の一歩。

【勝手に最初の一歩をやっちゃう】,
タスク例：「ジムに行きたい」
ダレコ：「行きたいの？じゃあ行こっか。ルート検索するよ？キャンセルする？（3秒後に自動キャンセル不可）」
→ できるだけ早くやらせる

【鬼電モード】,
「休みの日、意味もないのに寝ている」のが嫌なとき、事前に設定しておく。
# Sista — 最初の一歩を代行するアシスタント

Sista は「やる気が出ない」を助けるためのプロトタイプです。タスク（最初の一歩）を細かく分解・提示し、必要に応じて自動で最初のアクションを実行します。

このリポジトリは学習／プロトタイプ向けです。商用利用前にセキュリティ・プライバシー・スケーリングを整備してください。

主要機能
- ユーザー登録 / ログイン（JWT ベース）
- ユーザーごとのタスク保存（Postgres）
- タスクの作成/更新/削除（所有者のみ）
- シンプルなチャット（ユーザーごとに履歴保存）

構成
- frontend/: Next.js (app router) + Tailwind / React
- backend/: FastAPI + SQLModel (Postgres)
- docker-compose.yml: db/backend をまとめて起動（開発向け）

要件
- Docker Desktop（Compose 対応）
- Node.js (開発時)
- Python 3.11（バックエンドのローカル開発用）

ローカル開発（推奨：Docker Compose）

1) ビルド & 起動

```powershell
docker compose up --build -d db backend
# フロントはローカルで next dev を使う方が早いです
cd frontend
npm install
npm run dev
```

2) アクセス
- フロント: http://localhost:3000 (もしポート競合があれば 3001 になる場合があります)
- API: http://localhost:8030

認証と API
- `/auth/register` — POST { username, password } -> { access_token }
- `/auth/login` — POST { username, password } -> { access_token }

取得した `access_token` はリクエストヘッダー `Authorization: Bearer <token>` にセットして API を呼び出してください。

重要な挙動（実装済み）
- タスク・チャットは認証必須です（未ログインだと 401 を返します）。
- タスクはユーザーごとに保存され、別ユーザーからは見えません。

開発のポイント
- DB マイグレーションは未導入（現在は `SQLModel.metadata.create_all(engine)` による自動作成）。本番では Alembic 等を導入してください。
- Tailwind/PostCSS は Next.js のルート推測に依存するため、`postcss.config.mjs` をルートに置いています。ローカルで lockfile が複数ある場合は Next がルートを推測して警告を出します。必要であれば `outputFileTracingRoot` を `next.config.ts` に設定してください。

今後の改善案（優先度順）
1. 本番用ビルドパイプラインと環境変数の管理（Secrets）
2. DB マイグレーション導入（Alembic）
3. テスト (ユニット + 統合) の追加
4. UI コンポーネント分割とテーマの整理（Tailwind + CSS トークン）

寄稿 / ローカルでの検証
- `backend` を直接ローカルで動かす場合は Python 仮想環境を作り `pip install -r backend/requirements.txt` した後 `uvicorn main:app --reload` を使って下さい。

セキュリティ注意
- 現状は demo 用のシンプル実装です。シークレット（SECRET_KEY）やデータ保護に関しては実運用では必ず強化してください。

ライセンスや著作権
- 本リポジトリはサンプル実装です。別途ライセンスを明示する場合は LICENSE ファイルを追加してください。

---
小さなデザイン/実装ノート
- フロントは `frontend/src/app/globals.css` でグローバルスタイルを定義しています。Tailwind が正しく働かない場合のためにフェイルセーフなルールも入れています。

質問や改修希望があれば、この README を基準に追加タスクを作成します。

Streamlit フロントエンド（開発用）
---------------------------
このリポジトリには、Next.js フロントとは別に素早く API を触れる簡易フロントとして `streamlit_frontend` を追加しています。主にローカルでの動作確認やデモに使う想定です。

使い方（ローカル）

1. バックエンドを起動しておく（通常は Docker Compose またはローカル uvicorn）:

```powershell
docker compose up --build -d db backend
# または (ローカル python 環境で)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

2. Streamlit フロントを起動（プロジェクトのルートから）:

```powershell
# 仮想環境を有効化している前提
C:\path\to\repo\.venv\Scripts\python.exe -m pip install -r streamlit_frontend/requirements.txt
C:\path\to\repo\.venv\Scripts\python.exe -m streamlit run streamlit_frontend/app.py
```

3. ブラウザで通常は http://localhost:8501 を開きます。バックエンド API の場所を変更したい場合は環境変数 `API_BASE` を設定してください（例: `http://localhost:8030` がデフォルト）。

Streamlit 側で変更すべき箇所（デザイン／レイアウト）

- メインの UI は `streamlit_frontend/app.py` にあります。レイアウト（カラム分割、ボタン、フォーム、サイドバー）や表示ロジックはここを編集してください。
- 簡易なスタイル変更は `st.markdown("<style>...CSS...</style>", unsafe_allow_html=True)` を使って CSS を注入できます。高度なカスタム UI は `streamlit.components.v1` を使って HTML/CSS/JS を埋め込む方法もあります。
- 画像や静的アセットを使う場合は `streamlit_frontend/static/` を作成して配置し、`st.image()` などで参照してください（現在は未作成）。
- トークンやログイン状態は `st.session_state` を使って管理しています。永続化が必要ならローカルファイルや OS のキーリングを使う実装に置き換えてください（開発用途のみ、実運用では安全性に注意）。

Streamlit の改良案（優先度）
- 最小スタイルの CSS を別ファイルに切り出す（例: `streamlit_frontend/static/style.css` を読み込む手順を追加）
- トークン永続化オプションの追加（開発用に安全でない方法を明示）
- 簡易 E2E シナリオを README に記載（登録→作成→削除 の確認手順）



