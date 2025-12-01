import yaml
import logging
import sys
import argparse
import time
import os
import signal
import threading
from typing import Dict, Any

# コアロジックをインポート
from core import run_batch
from crypto_helper import PasswordCrypto

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
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
    
    stop_event = threading.Event()

    def signal_handler(signum, frame):
        logger.info(f"シグナル {signum} を受信しました。終了処理を開始します...")
        stop_event.set()

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
            
    logger.info("デーモンプロセスを終了します")

def main():
    parser = argparse.ArgumentParser(description='MailConsolidator: メール集約ツール')
    parser.add_argument('-d', '--daemon', action='store_true', help='デーモンモードで実行 (GUIなし)')
    parser.add_argument('-c', '--config', default='config.yaml', help='設定ファイルのパス (デフォルト: config.yaml)')
    
    args = parser.parse_args()
    
    config_path = args.config
    
    if args.daemon:
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
