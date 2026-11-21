# AIニュース → TikTok 自動スライド（iPadだけで設定できます）

毎日 **朝7時・夕方6時** ごろに、次のことを自動で行います。

1. 世界中のテックメディア（TechCrunch、The Verge、Ars Technica、MIT Technology Review、Techmeme、Google ニュース、ITmedia など）と Hacker News・Reddit からニュースを集める
2. 同じ話題の記事をまとめ、注目度（報じた媒体の数、反応の大きさ、新しさ、AI関連かどうか）で点数を付ける
3. 上位25本の候補からAI（Claude）が1本を選び、記事本文をもとに日本語のスライド原稿を書く
4. 縦長スライドを6〜7枚作る（表紙 → 要点3〜4枚 → なぜ重要？ → 出典とフォローのお願い）
5. TikTok の **下書き（受信箱）** に送る → iPad の TikTok アプリに通知が届くので、確認して公開

パソコンは不要です。動かす場所は GitHub Actions（無料）、画像を置く場所は GitHub Pages（無料）です。

---

## 必要なもの

| もの | 用途 | 費用 |
|---|---|---|
| GitHub アカウント | プログラムの実行と画像の公開 | 無料 |
| Anthropic API キー（console.anthropic.com） | ニュースの選定と要約 | 従量課金（使った分だけ） |
| TikTok for Developers アカウント | TikTok への送信 | 無料 |

---

## 手順（すべて iPad の Safari で操作）

### 1. GitHub にリポジトリを作る
1. github.com で「New repository」を押す
2. 名前を入力（例: `ai-news`）。**Public（公開）** を選ぶ（無料プランで GitHub Pages を使うのに必要です。パスワードなどの秘密情報は別の場所に保存されるので漏れません）
3. 「Create repository」を押す

### 2. ファイルをアップロードする
1. 受け取った zip ファイルを「ファイル」アプリで開いて展開する
2. GitHub のリポジトリ画面で「Add file」→「Upload files」→「choose your files」
3. 展開したフォルダの中のファイルを **すべて選択** してアップロードし、「Commit changes」を押す

### 3. 自動実行の設定ファイルを作る（ここだけ手入力）
フォルダ付きのファイルは iPad からはアップロードしにくいので、画面上で作ります。
1. 「Add file」→「Create new file」
2. ファイル名の欄に `.github/workflows/main.yml` と入力する（`/` を入力すると自動でフォルダになります）
3. 「ファイル」アプリで `main.yml` を開いて全文をコピーし、本文の欄に貼り付けて「Commit changes」を押す
4. （任意）一番上の階層にある `main.yml` は不要なので削除してかまいません

### 4. GitHub Pages を有効にする
1. リポジトリの「Settings」→「Pages」
2. Source を「Deploy from a branch」、Branch を `main`、フォルダを `/ (root)` にして「Save」を押す
3. 数分たつと、`https://ユーザー名.github.io/ai-news` が公開用のURLになります

### 5. 設定値を登録する
「Settings」→「Secrets and variables」→「Actions」を開きます。

**Variables タブ**（秘密でない設定）
| 名前 | 値の例 |
|---|---|
| `SITE_BASE_URL` | `https://ユーザー名.github.io/ai-news`（最後に `/` を付けない） |
| `ACCOUNT_HANDLE` | `@あなたのTikTokのID`（スライドに表示されます） |

**Secrets タブ**（秘密の設定）
| 名前 | 値 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic のAPIキー |

### 6. まずは画像だけ作ってみる（TikTokには送りません）
1. 「Actions」タブ →「AI News to TikTok」→「Run workflow」
2. mode が `preview` のまま「Run workflow」を押す
3. 5分ほどで完了します。実行結果のページに **スライドの画像とキャプション** が表示されます

ここで、ニュースの選び方や文章の雰囲気を確認できます。

### 7. TikTok のアプリを登録する（developers.tiktok.com）
1. TikTok アカウントでログインし、「Manage apps」→「Connect an app」でアプリを作る
2. アプリ情報を入力する
   - アイコン、名前、説明（例: 「自分のアカウントにAIニュースのスライドを投稿する個人用ツール」）
   - **Terms of Service URL**：`（SITE_BASE_URL）/terms.html`
   - **Privacy Policy URL**：`（SITE_BASE_URL）/privacy.html`
   - Platform は **Web**、Website URL は `（SITE_BASE_URL）/`
3. 「Add products」で **Login Kit** と **Content Posting API** を追加する
   - Login Kit の Redirect URI：`（SITE_BASE_URL）/callback.html`
   - Scopes：`user.info.basic` と `video.upload`
   - Content Posting API の **Direct Post は、最初はオフのまま** でかまいません
4. **URL properties** に、画像を置くURLとして `（SITE_BASE_URL）/` を「URL prefix」で追加する
   - 確認用のファイルが渡された場合は、手順2と同じ方法でリポジトリの一番上の階層にアップロードしてから「Verify」を押してください
   - もし github.io のURLを確認できない場合は、独自ドメインが必要になります（その場合はご相談ください）
5. 審査に申請する（数日〜2週間ほどかかります）。審査中も **Sandbox** に自分のアカウントを登録すれば試せます
6. 「Client key」と「Client secret」を控えておく

### 8. 残りの設定値を登録する
**Secrets タブ** に追加します。
| 名前 | 値 |
|---|---|
| `TIKTOK_CLIENT_KEY` | TikTok の Client key |
| `TIKTOK_CLIENT_SECRET` | TikTok の Client secret |
| `GH_PAT` | 下で作るトークン |

**GH_PAT の作り方**（TikTok のログイン情報を自動で更新して保存するために使います）
1. GitHub 右上のアイコン →「Settings」→「Developer settings」→「Personal access tokens」→「Fine-grained tokens」→「Generate new token」
2. Repository access で **このリポジトリだけ** を選ぶ
3. Permissions の **Secrets** を「Read and write」にする
4. 有効期限は最長に設定し、期限が来たら作り直してください

### 9. TikTok と連携する
1. Safari で `（SITE_BASE_URL）/callback.html` を開く
2. Client key を入力して「TikTokと連携」→ TikTok で許可する
3. 表示されたコードをコピーする
4. **すぐに**（コードの有効期限は短いため）GitHub の「Actions」→「Run workflow」で、mode を `setup`、code にコードを貼り付けて実行する
5. 成功すると `TIKTOK_REFRESH_TOKEN` が自動で保存されます

### 10. 試しに送ってみる
「Run workflow」で mode を `post` にして実行します。数分で iPad の TikTok アプリに通知が届きます。開いて内容を確認し、公開してください（TikTok アプリはバージョン 31.8 以上が必要です）。

**これで設定は完了です。** あとは毎日自動で動きます。

---

## 毎日の使い方
- 朝7時・夕方6時ごろに TikTok の受信箱へ下書きが届くので、確認して公開するだけです
- GitHub の定期実行は混雑すると数分〜30分ほど遅れることがあるため、6:40 と 17:40 に開始する設定にしています
- 内容に誤りがあれば、公開しないで破棄してください

## カスタマイズ
| 変えたいこと | 場所 |
|---|---|
| ニュースの取得元 | `config.py` の `FEEDS` |
| 実行時刻 | `.github/workflows/main.yml` の `cron`（UTC＝日本時間−9時間で書く） |
| 選び方・文章の雰囲気 | `llm.py` の `SELECT_SYSTEM` / `WRITE_SYSTEM` |
| デザイン・色 | `slides.py` |
| 下書きではなく自動で公開したい | TikTok の監査に通ったあと、Variables に `POST_MODE` = `DIRECT_POST` を追加し、連携ページで「自動公開も許可」にチェックを入れて手順9をやり直す |

## うまくいかないとき
- **Actions が赤くなる** → 実行結果を開き、赤い行のメッセージを確認してください。「設定が足りません」と出た場合は手順5・8を見直してください
- **「画像が公開されませんでした」** → 手順4の GitHub Pages の設定を確認してください
- **url_ownership_unverified** → 手順7-4の URL の確認がまだ済んでいません
- **トークン更新に失敗** → 手順9をやり直してください（長期間使わないと期限が切れます）

## 注意
- AIの要約は間違えることがあります。公開前に必ず内容を確認してください
- 元記事の文章や写真は使わず、AIが書いた要約とオリジナルのデザインだけで構成しています。出典は必ず表示されます
- 投稿には「AI生成」ラベルが付きます（不要なら Variables に `IS_AIGC` = `false` を追加）
