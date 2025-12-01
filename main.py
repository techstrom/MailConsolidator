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

# ... (PID related functions remain unchanged) ...

def main():
    # 内部フラグを先にチェック（argparseの前）
    if '--daemon-worker' in sys.argv:
        # Windows用の内部フラグ（バックグラウンドワーカー）
        # config_pathを取得
        config_path = 'config.yaml'
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
        config_path = 'config.yaml'
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
    
    # 通常のargparse処理
    parser = argparse.ArgumentParser(description='MailConsolidator: メール集約ツール')
    parser.add_argument('-d', '--daemon', action='store_true', help='デーモンモードで実行 (GUIなし)')
    parser.add_argument('-k', '--kill', action='store_true', help='バックグラウンドで実行中のデーモンを停止')
    parser.add_argument('-c', '--config', default='config.yaml', help='設定ファイルのパス (デフォルト: config.yaml)')
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
