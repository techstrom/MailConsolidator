# プログラム仕様書 (Program Specification)

## 1. システム構成

### 1.1 アーキテクチャ
MVC (Model-View-Controller) パターンに準じた構成を採用しているが、小規模アプリのため簡易的な構成となっている。

- **Model (Logic)**: `core.py`, `mail_client.py` - メール処理のコアロジック
- **View/Controller (GUI)**: `gui.py` - Tkinterによる画面表示とイベントハンドリング
- **Configuration**: `config.yaml` - 設定データ
- **Entry Point**: `main.py` - アプリケーション起動エントリ、デーモン管理機能

### 1.2 ファイル構成
- `main.py`: アプリケーションの起動スクリプト。コマンドライン引数の解析とGUI/デーモンモードの切り替え、デーモンプロセスの管理（起動・停止）、単一インスタンス制御を行う。
- `gui.py`: Tkinterを使用したGUIアプリケーションクラス `MailConsolidatorApp` と `IPCServer` を定義。Windows環境ではシステムトレイ機能も統合。
- `tray_icon.py`: Windows環境でのシステムトレイアイコン管理クラス `SystemTrayIcon` を定義（Windows専用）。
- `core.py`: メール集約の一括処理ロジック `run_batch`、プロセス管理用の `PIDManager` クラス、および設定ファイルパス管理用のヘルパー関数（`get_default_config_path`, `migrate_config_if_needed`）を定義。
- `mail_client.py`: メールサーバとの通信を行うクラス群 (`Pop3Source`, `ImapSource`, `ImapDestination`)。
- `crypto_helper.py`: パスワードの暗号化・復号化を行うユーティリティ。
- `config.yaml`: ユーザー設定ファイル（YAML形式）。プラットフォームに応じた適切な場所に保存される。

## 2. 詳細仕様

### 2.1 GUI仕様 (`gui.py`)

#### クラス: `MailConsolidatorApp`
- **初期化**: 設定ファイルの読み込み、ウィジェットの生成、ログハンドラの設定。
- **タブ構成**:
  1. **実行パネル**: 実行制御とログ・ステータス表示。
  2. **移動先設定**: 転送先IMAPサーバの設定フォーム。
  3. **取得元設定**: 取得元サーバのリストと編集フォーム。

#### 主要メソッド
- `__init__()`:
  - IPCサーバーを起動し、PIDファイルにプロセスIDとポート番号を書き込む。
  - システムトレイアイコンを初期化（Windows環境）。
- `toggle_background_task()`:
  - 定期実行の開始・停止を切り替える。
  - **開始時**: 別スレッド (`threading.Thread`) を作成し、`_background_loop` を実行。ボタン名を「定期実行を停止」に変更。
  - **停止時**: `stop_event` をセットし、ボタンを無効化（「停止処理中...」）。スレッド終了後にUIを初期状態に戻す。
- `_background_loop(interval)`:
  - 指定間隔で `run_batch` を呼び出すループ処理。
  - `stop_event` を監視し、安全にループを脱出する。
  - `finally` ブロックで `_reset_ui_state` を呼び出し、UIの整合性を保つ。
- `on_closing()`:
  - ウィンドウの閉じるボタン（×）が押されたときに呼ばれる。
  - カスタムダイアログを表示し、「アプリを終了」「バックグラウンド常駐」「キャンセル」から選択させる。
- `quit_app()`:
  - アプリケーションを完全に終了する。
  - PIDファイルを削除し、システムトレイアイコンを停止する。
- `update_source()`:
  - リストボックスで選択された設定を、入力フォームの内容で更新する。
  - **注意点**: `Listbox` の `exportselection=False` を設定し、フォーム編集時に選択が外れないようにしている。
  - 選択がない場合は警告メッセージを表示する。

#### クラス: `IPCServer`
- **目的**: プロセス間通信（IPC）サーバーとして動作し、他のプロセスからのコマンドを受信する。
- **実装**:
  - ローカルホスト（127.0.0.1）でソケットサーバーを起動。
  - ポート番号は自動割り当て（0を指定）。
  - 別スレッドでリスニングループを実行。
- **コマンド処理**:
  - `SHOW_WINDOW`: `app.show_window()` を呼び出してGUIを前面に表示。

### 2.2 コアロジック仕様 (`core.py`)

#### 関数: `run_batch(config, stop_event, callback)`
- 設定に基づき、全ての取得元ソースに対して処理を反復する。
- `stop_event` がセットされた場合、処理を中断する。
- `callback` を通じてGUIにステータス（取得完了、保存中、削除中など）を通知する。

#### 関数: `process_source(...)`
- 単一のソースに対する処理フロー:
  1. サーバ接続 (POP3/IMAP)。
  2. メッセージ一覧取得（IMAPは未読のみ）。

#### クラス: `PIDManager`
- **目的**: プロセスID（PID）とIPCポート番号の管理。
- **静的メソッド**:
  - `write_pid(port)`: PIDとポート番号をファイルに書き込む（形式: `<PID>:<PORT>`）。
  - `read_pid_info()`: PIDファイルから `(pid, port)` のタプルを読み込む。
  - `remove_pid()`: PIDファイルを削除する。
  - `is_process_running(pid)`: 指定されたPIDのプロセスが実行中かチェック。
  - `send_show_command(port)`: 指定されたポートに `SHOW_WINDOW` コマンドを送信（IPCクライアント機能）。

#### 関数: `get_default_config_path()`
- **目的**: プラットフォームに応じた適切な設定ファイルパスを返す。
- **パス**:
  - Windows: `%APPDATA%\MailConsolidator\config.yaml`
  - Unix系: `~/.config/MailConsolidator/config.yaml`
- **動作**: 必要に応じてディレクトリを自動作成。

#### 関数: `migrate_config_if_needed()`
- **目的**: 起動フォルダに古い設定ファイルがある場合、新しい場所にコピーする。
- **動作**:
  - 新しい場所に設定ファイルが既に存在する場合は何もしない。
  - 起動フォルダに `config.yaml` がある場合、`shutil.copy2` で新しい場所にコピー。
  - 古いファイルは削除されない（ユーザーが手動で削除可能）。

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

### 2.4 システムトレイ機能 (`tray_icon.py`)
- **クラス**: `SystemTrayIcon` (Windows専用)
- **機能**:
  - アプリケーションのシステムトレイ常駐化。
  - メニュー操作によるウィンドウの表示/非表示、バックグラウンド処理の切り替え、アプリ終了。
  - アイコンクリックでのウィンドウ表示。
- **GUI連携**:
  - `MailConsolidatorApp` と連携し、GUIの状態（表示/非表示）やバックグラウンド処理の状態を同期。
  - ウィンドウの「閉じる」操作は `on_closing()` メソッドで処理され、ダイアログで選択可能。

### 2.5 起動プロセス (`main.py`)
- **単一インスタンス制御**:
  - デフォルト起動時、`PIDManager.read_pid_info()` で既存インスタンスをチェック。
  - 既存プロセスが実行中の場合、`PIDManager.send_show_command(port)` でIPCコマンドを送信。
  - IPC通信成功時は新しいプロセスを起動せずに終了。
  - IPC通信失敗時または既存プロセスが存在しない場合は新しいインスタンスを起動。
- **起動モード**:
  - **デフォルト**: GUIをバックグラウンドで起動（`DETACHED_PROCESS`）。システムトレイに常駐。既存インスタンスがある場合はそのGUIを表示。
  - **フォアグラウンド (`-v`)**: GUIをフォアグラウンドで起動し、コンソールにログを表示。
  - **デーモン (`-d`)**: GUIなしでバックグラウンド実行。
- **PyInstaller対応**:
  - `sys.frozen` 属性をチェックし、exe化された環境とスクリプト実行環境の両方で正しくサブプロセスを起動するように分岐。
- **ログ制御**:
  - `-l` オプションにより、ログファイルへの出力を制御。指定がない場合はファイル出力を行わない。

### 2.6 デーモン管理機能
- **バックグラウンド実行**: コマンドライン引数 `-d` により、GUIなしでバックグラウンドプロセスとして起動可能とする。
- **デーモン停止**: コマンドライン引数 `-k` により、実行中のバックグラウンドプロセスを停止可能とする。
- **プロセス追跡**: PIDファイルを使用してバックグラウンドプロセスを追跡・管理する。
- **安全な終了**: デーモン停止時は、まず正常終了シグナル（SIGTERM）を送信し、応答がない場合は強制終了（SIGKILL）を行う。

#### コマンドライン引数
- `-d`, `--daemon`: デーモンモードで起動(バックグラウンド実行)。
- `-k`, `--kill`: 実行中のデーモンを停止して即座に終了。
- `-c`, `--config`: 設定ファイルのパスを指定(デフォルト: Windows: `%APPDATA%\MailConsolidator\config.yaml`, Unix系: `~/.config/MailConsolidator/config.yaml`)。
- `-v`, `--verbose`: 詳細ログをコンソールに表示。
- `-l`, `--log-file`: ログファイルのパスを指定。

### 2.7 セキュリティ仕様 (`crypto_helper.py`)
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
- **PyInstaller対応**: exe化のためのspecファイル作成、frozen環境対応。
- **システムトレイ実装**: Windows環境でのタスクトレイ常駐機能、メニュー操作の実装。
- **起動フロー改善**: デフォルトでのバックグラウンドGUI起動、ログファイル制御オプション追加。
- **デーモン管理機能追加**: `-k` オプションによるバックグラウンドデーモンの停止機能を追加。PIDファイルを使用したプロセス追跡・管理を実装。
- **GUI更新不具合修正**: `Listbox` の `exportselection=False` 設定により、編集時の選択解除を防止。
- **バックグラウンド実行改善**: 定期実行の開始/停止トグルボタンの実装、UIブロックの解消、停止処理中のフィードバック追加。
- **メール取得ロジック変更**: IMAP取得時に未読メールのみを対象とするよう変更。
- **保持ポリシー変更**: `delete_after_move=False` の場合、ステータスモニターに履歴を残すよう変更。
- **設定ファイル保存場所変更**: 起動フォルダからプラットフォーム固有の適切な場所（Windows: `%APPDATA%\MailConsolidator`, Unix系: `~/.config/MailConsolidator`）に変更。既存設定の自動移行機能を追加。
