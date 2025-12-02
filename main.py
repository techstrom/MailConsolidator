import yaml
import logging
import sys
import argparse
import time
import os
import signal
import threading
import subprocess
import tempfile
import psutil
import atexit
from typing import Dict, Any

# コアロジックをインポート
from core import run_batch, PIDManager, get_default_config_path, migrate_config_if_needed
from crypto_helper import PasswordCrypto

def setup_logging(verbose: bool, log_file: str = None):
    """ログ設定を初期化"""
    handlers = []
    if verbose:
        handlers.append(logging.StreamHandler(sys.stdout))
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    # ハンドラがない場合はNullHandlerを追加（エラー抑制）
    if not handlers:
        handlers.append(logging.NullHandler())
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # 既存の設定を上書き
    )

logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """設定ファイルを読み込み、パスワードを復号化する"""
    try:
        if not os.path.exists(config_path):
            logger.error(f"設定ファイルが見つかりません: {config_path}")
            sys.exit(1)
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        # パスワードを復号化
        crypto = PasswordCrypto()
        
        # 移動先パスワードを復号化
        if 'destination' in config and 'password' in config['destination']:
            password = config['destination']['password']
            if crypto.is_encrypted(password):
                try:
                    config['destination']['password'] = crypto.decrypt(password)
                except Exception as e:
                    logger.error(f"移動先パスワードの復号化に失敗しました: {e}")
                    sys.exit(1)
        
        # 取得元パスワードを復号化
        if 'sources' in config:
            for i, source in enumerate(config['sources']):
                if 'password' in source:
                    password = source['password']
                    if crypto.is_encrypted(password):
                        try:
                            source['password'] = crypto.decrypt(password)
                        except Exception as e:
                            logger.error(f"取得元 #{i+1} のパスワード復号化に失敗しました: {e}")
                            sys.exit(1)
        
        return config
    except Exception as e:
        logger.error(f"設定ファイルの読み込みに失敗しました: {e}")
        sys.exit(1)

def run_daemon(config_path: str):
    """デーモンモードで実行"""
    logger.info("デーモンモードで起動しました")
    
    # PIDファイルを作成
    PIDManager.write_pid(0)  # デーモンモードではポート不要
    
    stop_event = threading.Event()

    def signal_handler(signum, frame):
        logger.info(f"シグナル {signum} を受信しました。終了処理を開始します...")
        stop_event.set()
        # PIDファイルを削除
        PIDManager.remove_pid()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    while not stop_event.is_set():
        config = load_config(config_path)
        interval = config.get('interval', 3)
        
        try:
            logger.info("=== 定期実行開始 ===")
            result = run_batch(config, stop_event)
            logger.info(result)
        except Exception as e:
            logger.error(f"実行エラー: {e}")
            
        if stop_event.is_set():
            break
            
        logger.info(f"次回実行まで待機中... ({interval}分)")
        
        # interval分待機 (1秒ごとにstopフラグチェック)
        for _ in range(interval * 60):
            if stop_event.is_set():
                break
            time.sleep(1)
            
    # 正常終了時もPIDファイルを削除
    PIDManager.remove_pid()
    logger.info("デーモンプロセスを終了します")

def kill_daemon():
    """バックグラウンドで実行中のデーモンを停止する"""
    pid, port = PIDManager.read_pid_info()
    
    if pid is None:
        logger.error("PIDファイルが見つかりません。デーモンは起動していない可能性があります。")
        return False
    
    if not PIDManager.is_process_running(pid):
        logger.warning(f"PID {pid} のプロセスは実行されていません。")
        PIDManager.remove_pid()
        return False
    
    try:
        logger.info(f"デーモンプロセス (PID: {pid}) を停止しています...")
        process = psutil.Process(pid)
        process.terminate()
        
        # プロセスが終了するまで待機 (最大10秒)
        try:
            process.wait(timeout=10)
            logger.info("デーモンプロセスを正常に停止しました")
        except psutil.TimeoutExpired:
            logger.warning("プロセスが応答しないため、強制終了します")
            process.kill()
            logger.info("デーモンプロセスを強制終了しました")
        
        PIDManager.remove_pid()
        return True
        
    except psutil.NoSuchProcess:
        logger.error(f"PID {pid} のプロセスが見つかりません")
        PIDManager.remove_pid()
        return False
    except psutil.AccessDenied:
        logger.error(f"PID {pid} のプロセスへのアクセスが拒否されました")
        return False
    except Exception as e:
        logger.error(f"プロセスの停止中にエラーが発生しました: {e}")
        return False

def main():
    # PyInstallerの一時ディレクトリ削除エラーを抑制
    # この問題は既知のPyInstallerの制限で、アプリケーションの機能には影響しない
    if getattr(sys, 'frozen', False):
        # PyInstallerの一時ディレクトリクリーンアップエラーを抑制
        os.environ['PYINSTALLER_SUPPRESS_CLEANUP_ERRORS'] = '1'
    
    # 内部フラグを先にチェック（argparseの前）
    if '--daemon-worker' in sys.argv:
        # Windows用の内部フラグ（バックグラウンドワーカー）
        # config_pathを取得
        config_path = get_default_config_path()
        if '-c' in sys.argv:
            idx = sys.argv.index('-c')
            if idx + 1 < len(sys.argv):
                config_path = sys.argv[idx + 1]
        
        verbose = '-v' in sys.argv
        
        # ログファイル設定
        log_file = None
        if '-l' in sys.argv:
            idx = sys.argv.index('-l')
            if idx + 1 < len(sys.argv):
                log_file = sys.argv[idx + 1]
        
        setup_logging(verbose, log_file)
        run_daemon(config_path)
        return
    
    if '--gui-worker' in sys.argv:
        # Windows用の内部フラグ（GUIワーカー）
        # config_pathを取得
        config_path = get_default_config_path()
        if '-c' in sys.argv:
            idx = sys.argv.index('-c')
            if idx + 1 < len(sys.argv):
                config_path = sys.argv[idx + 1]
        
        # ログファイル設定
        log_file = None
        if '-l' in sys.argv:
            idx = sys.argv.index('-l')
            if idx + 1 < len(sys.argv):
                log_file = sys.argv[idx + 1]
        
        # ログファイルが指定されている場合のみログ出力
        if log_file:
            setup_logging(False, log_file)
            try:
                import tkinter as tk
                from gui import MailConsolidatorApp
                
                root = tk.Tk()
                app = MailConsolidatorApp(root, config_path=config_path)
                root.mainloop()
            except Exception as e:
                logging.error(f"GUI起動エラー: {e}")
                import traceback
                logging.error(traceback.format_exc())
        else:
            # ログなしで起動
            try:
                import tkinter as tk
                from gui import MailConsolidatorApp
                
                root = tk.Tk()
                app = MailConsolidatorApp(root, config_path=config_path)
                root.mainloop()
            except Exception:
                pass
        return
    
    # 設定ファイルの移行処理
    migrate_config_if_needed()
    
    # 通常のargparse処理
    parser = argparse.ArgumentParser(description='MailConsolidator: メール集約ツール')
    parser.add_argument('-d', '--daemon', action='store_true', help='デーモンモードで実行 (GUIなし)')
    parser.add_argument('-k', '--kill', action='store_true', help='バックグラウンドで実行中のデーモンを停止')
    parser.add_argument('-c', '--config', default=get_default_config_path(), help=f'設定ファイルのパス (デフォルト: {get_default_config_path()})')
    parser.add_argument('-v', '--verbose', action='store_true', help='詳細ログをコンソールに表示（GUIモード）')
    parser.add_argument('-l', '--log-file', help='ログファイルのパス（指定した場合のみファイルに出力）')
    
    args = parser.parse_args()
    
    # -k オプションが指定された場合、デーモンを停止して終了
    if args.kill:
        setup_logging(True, args.log_file)
        kill_daemon()
        sys.exit(0)
    
    config_path = args.config
    
    if args.daemon:
        # -d オプション: GUIなしでバックグラウンド実行
        setup_logging(args.verbose, args.log_file)
        
        if os.name == 'nt':  # Windows
            # 自分自身を再起動（--daemon-worker フラグ付き）
            if getattr(sys, 'frozen', False):
                # PyInstallerで凍結された場合
                cmd = [sys.executable, '--daemon-worker', '-c', config_path]
            else:
                # 通常のスクリプト実行
                cmd = [sys.executable, __file__, '--daemon-worker', '-c', config_path]
                
            if args.verbose:
                cmd.append('-v')
            
            if args.log_file:
                cmd.extend(['-l', args.log_file])
            
            # DETACHED_PROCESS フラグでバックグラウンド起動
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(
                cmd,
                creationflags=DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            logger.info("デーモンをバックグラウンドで起動しました")
        else:  # Unix系
            # フォークしてバックグラウンド実行
            pid = os.fork()
            if pid > 0:
                logger.info(f"デーモンをバックグラウンドで起動しました (PID: {pid})")
                sys.exit(0)
            # 子プロセスでデーモン実行
            run_daemon(config_path)
    else:
        # デフォルト: GUIモード
        if args.verbose:
            # -v オプション: フォアグラウンドでGUI起動（ログ表示）
            setup_logging(True, args.log_file)
            try:
                import tkinter as tk
                from gui import MailConsolidatorApp
                
                root = tk.Tk()
                app = MailConsolidatorApp(root, config_path=config_path)
                root.mainloop()
            except ImportError:
                logger.error("Tkinterが見つかりません。GUIモードを実行できません。")
                sys.exit(1)
            except Exception as e:
                logger.error(f"GUI起動エラー: {e}")
                import traceback
                traceback.print_exc()
        else:
            # オプションなし: バックグラウンドでGUI起動（プロンプトが戻る）
            
            # 既存インスタンスをチェック
            existing_pid, existing_port = PIDManager.read_pid_info()
            if existing_pid and PIDManager.is_process_running(existing_pid):
                # 既存のプロセスが実行中
                if existing_port and existing_port > 0:
                    # IPCでGUI表示を要求
                    print(f"既存のインスタンスが見つかりました (PID: {existing_pid})")
                    if PIDManager.send_show_command(existing_port):
                        print("GUIを表示しました")
                        sys.exit(0)
                    else:
                        print("既存インスタンスとの通信に失敗しました。新しいインスタンスを起動します...")
                        PIDManager.remove_pid()  # 古いPIDファイルを削除
                else:
                    print("既存のインスタンスが見つかりましたが、IPC情報がありません。新しいインスタンスを起動します...")
                    PIDManager.remove_pid()
            elif existing_pid:
                # PIDファイルは存在するがプロセスが動いていない
                print("古いPIDファイルを削除します...")
                PIDManager.remove_pid()
            
            if os.name == 'nt':  # Windows
                # 自分自身を再起動（--gui-worker フラグ付き）
                if getattr(sys, 'frozen', False):
                    # PyInstallerで凍結された場合
                    cmd = [sys.executable, '--gui-worker', '-c', config_path]
                else:
                    # 通常のスクリプト実行
                    cmd = [sys.executable, __file__, '--gui-worker', '-c', config_path]
                
                if args.log_file:
                    cmd.extend(['-l', args.log_file])
                
                # DETACHED_PROCESS フラグでバックグラウンド起動
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen(
                    cmd,
                    creationflags=DETACHED_PROCESS,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL
                )
                print("GUIをバックグラウンドで起動しました")
            else:  # Unix系
                # フォークしてバックグラウンド実行
                pid = os.fork()
                if pid > 0:
                    print(f"GUIをバックグラウンドで起動しました (PID: {pid})")
                    sys.exit(0)
                # 子プロセスでGUI実行
                try:
                    import tkinter as tk
                    from gui import MailConsolidatorApp
                    
                    root = tk.Tk()
                    app = MailConsolidatorApp(root, config_path=config_path)
                    root.mainloop()
                except Exception:
                    pass  # バックグラウンドなのでエラーは無視

if __name__ == "__main__":
    main()
