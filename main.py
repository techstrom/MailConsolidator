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
from typing import Dict, Any

# コアロジックをインポート
from core import run_batch
from crypto_helper import PasswordCrypto

def setup_logging(verbose: bool):
    """ログ設定を初期化"""
    handlers = []
    if verbose:
        handlers.append(logging.StreamHandler(sys.stdout))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # 既存の設定を上書き
    )

logger = logging.getLogger(__name__)

# PIDファイルのパス
PID_FILE = os.path.join(tempfile.gettempdir(), 'mailconsolidator.pid')

def write_pid_file():
    """現在のプロセスIDをPIDファイルに書き込む"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"PIDファイルを作成しました: {PID_FILE}")
    except Exception as e:
        logger.error(f"PIDファイルの作成に失敗しました: {e}")

def read_pid_file():
    """PIDファイルからプロセスIDを読み込む"""
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                return int(f.read().strip())
    except Exception as e:
        logger.error(f"PIDファイルの読み込みに失敗しました: {e}")
    return None

def remove_pid_file():
    """PIDファイルを削除する"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            logger.info(f"PIDファイルを削除しました: {PID_FILE}")
    except Exception as e:
        logger.error(f"PIDファイルの削除に失敗しました: {e}")

def is_process_running(pid):
    """指定されたPIDのプロセスが実行中かチェック"""
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

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
    write_pid_file()
    
    stop_event = threading.Event()

    def signal_handler(signum, frame):
        logger.info(f"シグナル {signum} を受信しました。終了処理を開始します...")
        stop_event.set()
        # PIDファイルを削除
        remove_pid_file()

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
    remove_pid_file()
    logger.info("デーモンプロセスを終了します")

def kill_daemon():
    """バックグラウンドで実行中のデーモンを停止する"""
    pid = read_pid_file()
    
    if pid is None:
        logger.error("PIDファイルが見つかりません。デーモンは起動していない可能性があります。")
        return False
    
    if not is_process_running(pid):
        logger.warning(f"PID {pid} のプロセスは実行されていません。")
        remove_pid_file()
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
        
        remove_pid_file()
        return True
        
    except psutil.NoSuchProcess:
        logger.error(f"PID {pid} のプロセスが見つかりません")
        remove_pid_file()
        return False
    except psutil.AccessDenied:
        logger.error(f"PID {pid} のプロセスへのアクセスが拒否されました")
        return False
    except Exception as e:
        logger.error(f"プロセスの停止中にエラーが発生しました: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='MailConsolidator: メール集約ツール')
    parser.add_argument('-d', '--daemon', action='store_true', help='デーモンモードで実行 (GUIなし)')
    parser.add_argument('-k', '--kill', action='store_true', help='バックグラウンドで実行中のデーモンを停止')
    parser.add_argument('-c', '--config', default='config.yaml', help='設定ファイルのパス (デフォルト: config.yaml)')
    parser.add_argument('-v', '--verbose', action='store_true', help='詳細ログをコンソールに表示')
    
    args = parser.parse_args()
    
    # ログ設定を初期化
    setup_logging(args.verbose)
    
    # -k オプションが指定された場合、デーモンを停止して終了
    if args.kill:
        kill_daemon()
        sys.exit(0)
    
    config_path = args.config
    
    if args.daemon:
        # バックグラウンドでデーモンを起動
        if os.name == 'nt':  # Windows
            # 自分自身を再起動（--daemon-worker フラグ付き）
            cmd = [sys.executable, __file__, '--daemon-worker', '-c', config_path]
            if args.verbose:
                cmd.append('-v')
            
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
    elif '--daemon-worker' in sys.argv:
        # Windows用の内部フラグ（バックグラウンドワーカー）
        run_daemon(config_path)
    else:
        # GUIモード
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

if __name__ == "__main__":
    main()
