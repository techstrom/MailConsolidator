# プログラム仕様書 (Program Specification)

## 1. システム構成

### 1.1 アーキテクチャ
MVC (Model-View-Controller) パターンに準じた構成を採用しているが、小規模アプリのため簡易的な構成となっている。

- **Model (Logic)**: `core.py`, `mail_client.py` - メール処理のコアロジック
- **View/Controller (GUI)**: `gui.py` - Tkinterによる画面表示とイベントハンドリング
- **Configuration**: `config.yaml` - 設定データ
- **Entry Point**: `main.py` - アプリケーション起動エントリ、デーモン管理機能

### 1.2 ファイル構成
- `main.py`: アプリケーションの起動スクリプト。コマンドライン引数の解析とGUI/デーモンモードの切り替え、デーモンプロセスの管理（起動・停止）を行う。起動モード（デフォルト/フォアグラウンド/デーモン）の制御も担当。
- `gui.py`: Tkinterを使用したGUIアプリケーションクラス `MailConsolidatorApp` を定義。Windows環境ではシステムトレイ機能も統合。
- `tray_icon.py`: Windows環境でのシステムトレイアイコン管理クラス `SystemTrayIcon` を定義（Windows専用）。
- `core.py`: メール集約の一括処理ロジック `run_batch` を定義。
- `mail_client.py`: メールサーバとの通信を行うクラス群 (`Pop3Source`, `ImapSource`, `ImapDestination`)。
- `crypto_helper.py`: パスワードの暗号化・復号化を行うユーティリティ。
- `config.yaml`: ユーザー設定ファイル（YAML形式）。

## 2. 詳細仕様

### 2.1 GUI仕様 (`gui.py`)

#### クラス: `MailConsolidatorApp`
- **初期化**: 設定ファイルの読み込み、ウィジェットの生成、ログハンドラの設定。
- **タブ構成**:
  1. **実行パネル**: 実行制御とログ・ステータス表示。
  2. **移動先設定**: 転送先IMAPサーバの設定フォーム。
  3. **取得元設定**: 取得元サーバのリストと編集フォーム。

#### 主要メソッド
- `toggle_background_task()`:
  - 定期実行の開始・停止を切り替える。
  - **開始時**: 別スレッド (`threading.Thread`) を作成し、`_background_loop` を実行。ボタン名を「定期実行を停止」に変更。
  - **停止時**: `stop_event` をセットし、ボタンを無効化（「停止処理中...」）。スレッド終了後にUIを初期状態に戻す。
- `_background_loop(interval)`:
  - 指定間隔で `run_batch` を呼び出すループ処理。
  - `stop_event` を監視し、安全にループを脱出する。
  - `finally` ブロックで `_reset_ui_state` を呼び出し、UIの整合性を保つ。
- `update_source()`:
  - リストボックスで選択された設定を、入力フォームの内容で更新する。
  - **注意点**: `Listbox` の `exportselection=False` を設定し、フォーム編集時に選択が外れないようにしている。
  - 選択がない場合は警告メッセージを表示する。

### 2.2 コアロジック仕様 (`core.py`)

#### 関数: `run_batch(config, stop_event, callback)`
- 設定に基づき、全ての取得元ソースに対して処理を反復する。
- `stop_event` がセットされた場合、処理を中断する。
- `callback` を通じてGUIにステータス（取得完了、保存中、削除中など）を通知する。

#### 関数: `process_source(...)`
- 単一のソースに対する処理フロー:
  1. サーバ接続 (POP3/IMAP)。
  2. メッセージ一覧取得（IMAPは未読のみ）。

#### クラス: `Pop3Source`
- `get_messages()`: 全メッセージを取得する(POP3の仕様上、未読管理はクライアント側で行う必要があるが、本仕様では全件取得とし、重複排除は行わないため `delete_after_move=True` 推奨)。

### 2.3 メールクライアント仕様 (`mail_client.py`)

#### クラス: `ImapSource`
- `get_messages()`: `SEARCH UNSEEN` コマンドを使用し、未読メールのみを取得する。
- `mark_as_read(uid)`: 指定されたUIDのメールに `\Seen` フラグを付与する。

#### クラス: `ImapDestination`
  8. 終了後、`remove_pid_file()` でPIDファイルを削除。
- エラーハンドリング:
  - `psutil.NoSuchProcess`: プロセスが見つからない場合、PIDファイルを削除。
  - `psutil.AccessDenied`: アクセス拒否エラーを表示。
  - その他の例外: エラーメッセージを表示。

#### コマンドライン引数
- `-d`, `--daemon`: デーモンモードで起動(バックグラウンド実行)。
- `-k`, `--kill`: 実行中のデーモンを停止して即座に終了。
- `-c`, `--config`: 設定ファイルのパスを指定(デフォルト: `config.yaml`)。
- `-v`, `--verbose`: 詳細ログをコンソールに表示。

### 2.5 セキュリティ仕様 (`crypto_helper.py`)
- パスワードの暗号化・復号化を行う `PasswordCrypto` クラスを提供。
- 設定ファイル内のパスワードは暗号化して保存される。

## 3. データ構造

### 3.1 設定ファイル (`config.yaml`)
```yaml
interval: 3          # 実行間隔（分）
destination:           # 転送先設定
  host: str
  port: int
  user: str
  password: str        # 暗号化済み
  ssl: bool
  folder: str
sources:               # 取得元リスト
  - protocol: str      # 'imap' or 'pop3'
    host: str
    port: int
    user: str
    password: str      # 暗号化済み
    ssl: bool
    folder: str
    delete_after_move: bool
```

## 4. 変更履歴 (Recent Changes)
- **デーモン管理機能追加**: `-k` オプションによるバックグラウンドデーモンの停止機能を追加。PIDファイルを使用したプロセス追跡・管理を実装。
- **GUI更新不具合修正**: `Listbox` の `exportselection=False` 設定により、編集時の選択解除を防止。
- **バックグラウンド実行改善**: 定期実行の開始/停止トグルボタンの実装、UIブロックの解消、停止処理中のフィードバック追加。
- **メール取得ロジック変更**: IMAP取得時に未読メールのみを対象とするよう変更。
- **保持ポリシー変更**: `delete_after_move=False` の場合、ステータスモニターに履歴を残すよう変更。
