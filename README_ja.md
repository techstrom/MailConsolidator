# MailConsolidator
[日本語版 (Japanese)](README_ja.md) | [English](README_en.md)

複数のメールアカウント（POP3/IMAP）から1つのIMAPサーバにメールを集約するPythonアプリケーションです。
2026年1月からgmailでのPOPサポート（他のメールサーバからPOPでメールを取得する機能）が終了するので、その代わりに使えるツールとして作成しています。他のPOPメールを取得してimapでgmailに押し込むので、このアプリを動かしておけば、今までと同様にgmailに他のPOPメールを集約して使うことができます。

## 概要

MailConsolidatorは、複数のメールサーバからメールを取得し、指定したIMAPサーバに転送することで、メールを一元管理できるツールです。GUIとコマンドラインの両方に対応しており、定期的な自動実行も可能です。

## 主な機能

- **複数プロトコル対応**: POP3とIMAPの両方から取得可能
- **未読メールのみ取得**: IMAPの場合、未読メールのみを効率的に取得
- **自動実行**: 指定した間隔で自動的にメール集約を実行
- **リアルタイムモニタリング**: GUI上でメール処理状況をリアルタイムで確認
- **システムトレイ常駐**: Windows環境ではタスクトレイに常駐し、バックグラウンドで動作
- **単一インスタンス制御**: 既に起動している場合は既存のGUIを表示（IPC通信）
- **柔軟な削除設定**: 取得元サーバにメールを残すか削除するかを選択可能
- **SSL/TLS暗号化**: セキュアな通信をサポート
- **Windows インストーラー**: 簡単にインストールできる Windows インストーラーを提供

## 必要要件

- Python 3.7以降
- PyYAML
- psutil
- cryptography
- pystray (Windowsシステムトレイ用)
- Pillow (画像処理用)
- certifi (SSL証明書用)

## インストール

### Windows ユーザー向け（推奨）

Windows インストーラーを使用すると、簡単にインストールできます：

1. **インストーラーをダウンロード**:
   - [MailConsolidator-Setup-1.0.0.exe](https://github.com/techstrom/MailConsolidator/releases/download/v1.0.0/MailConsolidator-Setup-1.0.0.exe) をダウンロード

2. **インストーラーを実行**:
   - ダウンロードした `MailConsolidator-Setup-1.0.0.exe` をダブルクリック
   - インストールウィザードの指示に従ってインストール

3. **起動**:
   - スタートメニューまたはデスクトップアイコンから起動

### 開発者向け（ソースから実行）

1. リポジトリをクローンまたはダウンロード
```bash
git clone <repository-url>
cd MailConsolidator
```

2. 依存パッケージをインストール
```bash
pip install -r requirements.txt
```

3. Python スクリプトとして実行
```bash
python main.py
```

## 使い方

### GUIモード（推奨）

GUIを起動して設定と実行を行います：

```bash
python main.py
```
または、GitHubリポジトリの `dist` フォルダにある [`MailConsolidator.exe`](./dist/MailConsolidator.exe) をダウンロードして直接実行することも可能です。

**単一インスタンス制御**: 既にアプリケーションが起動している場合、新しいプロセスは起動せず、既存のGUIウィンドウが自動的に表示されます。バックグラウンドで実行中のタスクは中断されません。

#### GUI操作方法

1. **移動先設定タブ**: 
   - 転送先IMAPサーバの情報を入力
   - 「設定を保存」をクリック

2. **取得元設定タブ**:
   - 「新規追加」で取得元アカウントを追加
   - プロトコル（POP3/IMAP）、サーバ情報、認証情報を入力
   - 「移動後に削除」チェックボックスで削除設定を選択
   - 複数のアカウントを登録可能

3. **実行パネル**:
   - 「今すぐ実行」: 即座にメール集約を実行
   - 「定期実行を開始/停止」: 指定した間隔（分単位）で自動実行のON/OFFを切り替え
     - **自動保存**: 実行間隔を変更してフォーカスを外すと、自動的に設定ファイルに保存されます。
   - 「アプリを終了」: アプリケーションを完全に終了（右端に配置）
   - メール処理状況モニター: リアルタイムで処理状況を確認

4. **ウィンドウを閉じる（×ボタン）**:
   - ダイアログが表示され、以下から選択できます：
     - **アプリを終了**: アプリケーションを完全に終了
     - **バックグラウンド常駐**: ウィンドウを非表示にしてシステムトレイに常駐
     - **キャンセル**: 操作を取り消す

### 起動モード

#### デフォルト起動（バックグラウンド）

オプションなしで起動すると、GUIがバックグラウンドで起動し、すぐにプロンプトが戻ります：

```bash
python main.py
```

**既存インスタンスがある場合**: 新しいプロセスは起動せず、既存のGUIウィンドウが前面に表示されます。

Windows環境では、システムトレイにアイコンが表示され、以下の操作が可能です：
- **ウィンドウを表示/非表示**: GUIの表示切り替え
- **定期実行の切り替え**: バックグラウンド処理のON/OFF
- **終了**: アプリケーションの完全終了

#### GUIフォアグラウンドモード

詳細ログをコンソールに表示しながらGUIを起動します（デバッグ用）：

```bash
python main.py -v
```

#### デーモンモード（GUIなし）

GUIを表示せずにバックグラウンドで実行します：

```bash
python main.py -d
```

#### オプション一覧

- `-d`, `--daemon`: デーモンモードで実行（GUIなし、バックグラウンド実行）
- `-k`, `--kill`: バックグラウンドで実行中のデーモンを停止
- `-c`, `--config`: 設定ファイルのパスを指定（デフォルト: Windows: `%APPDATA%\MailConsolidator\config.yaml`, Unix系: `~/.config/MailConsolidator/config.yaml`）
- `-v`, `--verbose`: 詳細ログをコンソールに表示（GUIモード）
- `-l`, `--log-file`: ログファイルのパスを指定（指定した場合のみファイルに出力）

例：
```bash
# デフォルト: GUIをバックグラウンドで起動（プロンプトが戻る、ログなし）
python main.py

# ログファイルに出力しながら起動
python main.py -l app.log

# GUIをフォアグラウンドで起動（コンソールログあり）
python main.py -v

# デーモンモード（GUIなし、ログファイル出力）
python main.py -d -l daemon.log

# バックグラウンドで実行中のデーモンを停止
python main.py -k
```

### デーモンの管理

バックグラウンドで起動したデーモンは、以下の方法で停止できます：

1. **システムトレイから終了**（Windows GUIモード）:
   タスクトレイアイコンを右クリックして「終了」を選択します。

2. **GUIの「アプリを終了」ボタン**:
   メイン画面の「アプリを終了」ボタンをクリックします。

3. **-kオプションを使用**:
   ```bash
   python main.py -k
   ```
   このコマンドは、実行中のデーモンプロセスを検出して停止し、即座に終了します。

4. **プロセスを直接終了**:
   - Windows: タスクマネージャーでPythonプロセスを終了
   - Unix系: `kill` コマンドでプロセスを終了

デーモンプロセスの状態は、システムの一時ディレクトリに作成される `mailconsolidator.pid` ファイルで管理されます。

## ドキュメント

詳細な仕様や要件については、以下のドキュメントを参照してください：

- [要件定義書 (REQUIREMENTS.md)](./REQUIREMENTS.md)
- [プログラム仕様書 (SPECIFICATION.md)](./SPECIFICATION.md)

## Gmail利用時の重要な注意事項

### Gmailアプリパスワードの設定

Gmailアカウントで2段階認証を有効にしている場合、通常のパスワードではなく**アプリパスワード**を使用する必要があります。

#### アプリパスワードの取得手順

1. Googleアカウントにログイン
2. [Googleアカウント管理](https://myaccount.google.com/) にアクセス
3. 左メニューから「セキュリティ」を選択
4. 「Googleへのログイン」セクションで「2段階認証プロセス」をクリック
5. ページ下部の「アプリパスワード」をクリック
6. アプリを選択: 「メール」
7. デバイスを選択: 「Windowsパソコン」（または該当するもの）
8. 「生成」をクリック
9. 表示された16文字のパスワードをコピー
10. MailConsolidatorの設定画面のパスワード欄に貼り付け

**注意**: アプリパスワードはスペースなしで入力してください。

### Gmail IMAP設定

Gmailアカウントで以下の設定を確認してください：

- IMAPアクセスが有効になっていること（Gmail設定 → 「メール転送と POP/IMAP」）
- ホスト: `imap.gmail.com`
- ポート: `993`
- SSL: 有効

## 設定ファイル（config.yaml）

### 設定ファイルの保存場所

設定ファイルは、プラットフォームに応じた適切な場所に自動的に保存されます：

- **Windows**: `%APPDATA%\MailConsolidator\config.yaml`
  - 例: `C:\Users\あなたのユーザー名\AppData\Roaming\MailConsolidator\config.yaml`
- **Unix系**: `~/.config/MailConsolidator/config.yaml`

**既存の設定ファイルの移行**: 起動フォルダに古い `config.yaml` がある場合、初回起動時に自動的に新しい場所にコピーされます。古いファイルは削除されません。

**カスタムパス**: `-c` オプションで任意の場所を指定できます：
```bash
python main.py -c "C:\custom\path\to\config.yaml"
```

### 設定ファイルの構造

設定ファイルは以下の構造になっています：

```yaml
interval: 3  # 定期実行の間隔（分）

destination:
  host: imap.example.com
  port: 993
  user: dest_user@example.com
  password: your_password_or_app_password
  ssl: true
  folder: INBOX

sources:
  - protocol: imap  # または pop3
    host: imap.gmail.com
    port: 993
    user: source@gmail.com
    password: your_gmail_app_password  # Gmailアプリパスワード
    ssl: true
    folder: INBOX  # IMAPのみ
    delete_after_move: false  # trueで転送後に削除

  - protocol: pop3
    host: pop.example.com
    port: 995
    user: source2@example.com
    password: password
    ssl: true
    delete_after_move: true
```

### 設定項目の説明

#### destination（転送先）
- `host`: IMAPサーバのホスト名
- `port`: ポート番号（通常993）
- `user`: ユーザー名（メールアドレス）
- `password`: パスワード（Gmailの場合はアプリパスワード）
- `ssl`: SSL/TLS接続を使用（推奨: `true`）
- `folder`: 転送先フォルダ（デフォルト: `INBOX`）

#### sources（取得元）
- `protocol`: `imap` または `pop3`
- `host`: メールサーバのホスト名
- `port`: ポート番号（POP3: 995、IMAP: 993）
- `user`: ユーザー名（メールアドレス）
- `password`: パスワード（Gmailの場合はアプリパスワード）
- `ssl`: SSL/TLS接続を使用（推奨: `true`）
- `folder`: 取得元フォルダ（IMAPのみ、デフォルト: `INBOX`）
- `delete_after_move`: 転送後に元サーバから削除するか
  - `true`: 削除する（推奨: POP3）
  - `false`: 保持する（IMAP推奨 - 既読マークを付けて次回取得対象外）

## 動作の詳細

### IMAP + delete_after_move: false の場合
1. 未読メールのみを取得
2. 転送先に送信
3. 元サーバで既読マークを付ける
4. 次回実行時は既読のため取得されない
5. ステータスモニターに「完了（保持）」と表示

### IMAP + delete_after_move: true の場合
1. 未読メールのみを取得
2. 転送先に送信
3. 元サーバから削除
4. ステータスモニターから削除

### POP3の注意点
- POP3には未読/既読の概念がないため、`delete_after_move: false`の場合、毎回同じメールが取得されます
- POP3では`delete_after_move: true`の使用を推奨します

## トラブルシューティング

### 認証エラーが発生する

**症状**: `[AUTHENTICATIONFAILED] Invalid credentials`

**解決方法**:
1. Gmailの場合、アプリパスワードを使用しているか確認
2. パスワードにスペースが含まれていないか確認
3. 2段階認証が有効になっているか確認（Gmail）

### メールが重複して取得される

**症状**: 同じメールが何度も転送される

**解決方法**:
- IMAPの場合: `delete_after_move: false`で既読マークが正しく付いているか確認
- POP3の場合: `delete_after_move: true`に変更して削除する

### 接続できない

**症状**: サーバに接続できない

**解決方法**:
1. ホスト名とポート番号が正しいか確認
2. SSL設定が正しいか確認（Gmailは`ssl: true`）
3. ファイアウォールでブロックされていないか確認
4. IMAPアクセスが有効になっているか確認（Gmail設定）

### exe実行時にSSLエラーが発生する

**症状**: `[Errno 2] No such file or directory: ... base_library.zip`

**解決方法**:
最新のバージョンでは `certifi` を使用して修正されています。最新のコードを取得して再ビルドしてください。
```bash
pip install certifi
pyinstaller MailConsolidator.spec
```

## ライセンス

このプロジェクトは[MITライセンス](./LICENSE)の下で公開されています。

## 注意事項

- 設定ファイル（`config.yaml`）にはパスワードが暗号化されて保存されますが、ファイルのアクセス権限に注意してください
- 大量のメールを処理する場合、初回実行に時間がかかる場合があります
- メールサーバの接続数制限に注意してください（短時間に大量の接続を行うとブロックされる可能性があります）

