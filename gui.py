import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import yaml
import threading
import time
import logging
import queue
import os
from typing import Dict, Any

# core.py からロジックをインポート
# core.py からロジックをインポート
from core import run_batch, PIDManager
from crypto_helper import PasswordCrypto
import copy
import socket

# Windows環境でのみシステムトレイをインポート
if os.name == 'nt':
    try:
        from tray_icon import SystemTrayIcon
        TRAY_AVAILABLE = True
    except ImportError:
        TRAY_AVAILABLE = False
else:
    TRAY_AVAILABLE = False

class IPCServer:
    def __init__(self, app):
        self.app = app
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('127.0.0.1', 0)) # 0 means auto-assign port
        self.port = self.sock.getsockname()[1]
        self.sock.listen(1)
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        logging.info(f"IPCサーバーを開始しました (Port: {self.port})")

    def _listen_loop(self):
        while True:
            try:
                conn, addr = self.sock.accept()
                with conn:
                    data = conn.recv(1024)
                    if data == b'SHOW_WINDOW':
                        logging.info("GUI表示リクエストを受信しました")
                        self.app.root.after(0, self.app.show_window)
            except Exception as e:
                logging.error(f"IPCサーバーエラー: {e}")
                break

class QueueHandler(logging.Handler):
    """ログをキューに保存するハンドラ"""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))

class GuiLogHandler:
    """キューからログを取り出してGUIを更新するクラス"""
    def __init__(self, text_widget, log_queue, interval_ms=100):
        self.text_widget = text_widget
        self.log_queue = log_queue
        self.interval_ms = interval_ms
        self.update_log()

    def update_log(self):
        try:
            messages = []
            while True:
                try:
                    msg = self.log_queue.get_nowait()
                    messages.append(msg)
                    if len(messages) > 100: # 一度に処理する最大数
                        break
                except queue.Empty:
                    break
            
            if messages:
                self.text_widget.configure(state='normal')
                self.text_widget.insert(tk.END, '\n'.join(messages) + '\n')
                self.text_widget.see(tk.END)
                self.text_widget.configure(state='disabled')
        finally:
            self.text_widget.after(self.interval_ms, self.update_log)

class MailConsolidatorApp:
    def __init__(self, root, config_path='config.yaml'):
        self.root = root
        self.config_path = config_path
        self.root.title(f"MailConsolidator Manager ({self.config_path})")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.config = self.load_config()
        self.is_running = False
        self.is_background_running = False  # トレイメニュー用
        self.stop_event = threading.Event()
        self.bg_thread = None
        self.tray_icon = None
        self.ipc_server = None

        self.create_widgets()
        self.setup_logging()
        
        # IPCサーバー起動とPIDファイル作成
        try:
            self.ipc_server = IPCServer(self)
            PIDManager.write_pid(self.ipc_server.port)
        except Exception as e:
            logging.error(f"IPCサーバーの起動に失敗しました: {e}")
            # IPC失敗しても起動は継続するが、PIDファイルは作成されないかも
        
        # Windows環境ならシステムトレイを初期化
        if TRAY_AVAILABLE:
            self.tray_icon = SystemTrayIcon(self)
            self.tray_icon.run()
            logging.info("システムトレイアイコンを起動しました")

    def on_closing(self):
        # カスタムダイアログを作成
        dialog = tk.Toplevel(self.root)
        dialog.title("終了確認")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        
        # モーダルにする
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 画面中央に配置
        try:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
            dialog.geometry(f"+{x}+{y}")
        except Exception:
            pass # 座標計算に失敗した場合はデフォルト位置
        
        ttk.Label(dialog, text="ウィンドウを閉じようとしています。\nどのように処理しますか？", padding=20, justify='center').pack()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', padx=20, pady=10)
        
        def on_quit():
            dialog.destroy()
            self.quit_app()
            
        def on_hide():
            dialog.destroy()
            self.hide_window()
            
        def on_cancel():
            dialog.destroy()
            
        # ボタン配置
        ttk.Button(btn_frame, text="アプリを終了", command=on_quit).pack(side='left', expand=True, padx=5)
        if TRAY_AVAILABLE:
            ttk.Button(btn_frame, text="バックグラウンド常駐", command=on_hide).pack(side='left', expand=True, padx=5)
        ttk.Button(btn_frame, text="キャンセル", command=on_cancel).pack(side='left', expand=True, padx=5)
        
        # Xボタンでキャンセル扱い
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        
        self.root.wait_window(dialog)

    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                # パスワードを復号化してメモリ上に保持
                try:
                    crypto = PasswordCrypto()
                    
                    # 移動先パスワード
                    if 'destination' in config and 'password' in config['destination']:
                        pwd = config['destination']['password']
                        if crypto.is_encrypted(pwd):
                            config['destination']['password'] = crypto.decrypt(pwd)
                    
                    # 取得元パスワード
                    if 'sources' in config:
                        for source in config['sources']:
                            if 'password' in source:
                                pwd = source['password']
                                if crypto.is_encrypted(pwd):
                                    source['password'] = crypto.decrypt(pwd)
                                    
                except Exception as e:
                    logging.error(f"パスワード復号化エラー: {e}")
                    # 復号化に失敗しても、設定自体は返す（パスワード再入力で直せるように）
                
                return config
            except Exception as e:
                messagebox.showerror("エラー", f"設定ファイルの読み込みに失敗しました: {e}")
                return {}
        return {'destination': {}, 'sources': [], 'interval': 3}

    def save_config(self):
        try:
            # 保存用に設定をコピーして暗号化
            config_to_save = copy.deepcopy(self.config)
            crypto = PasswordCrypto()
            
            # 移動先パスワード暗号化
            if 'destination' in config_to_save and 'password' in config_to_save['destination']:
                pwd = config_to_save['destination']['password']
                if pwd and not crypto.is_encrypted(pwd):
                    config_to_save['destination']['password'] = crypto.encrypt(pwd)
            
            # 取得元パスワード暗号化
            if 'sources' in config_to_save:
                for source in config_to_save['sources']:
                    if 'password' in source:
                        pwd = source['password']
                        if pwd and not crypto.is_encrypted(pwd):
                            source['password'] = crypto.encrypt(pwd)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_to_save, f, allow_unicode=True, default_flow_style=False)
            # messagebox.showinfo("保存", "設定を保存しました")
        except Exception as e:
            messagebox.showerror("エラー", f"設定ファイルの保存に失敗しました: {e}")

    def create_widgets(self):
        # タブコントロール
        tab_control = ttk.Notebook(self.root)
        
        self.tab_control_panel = ttk.Frame(tab_control)
        self.tab_settings = ttk.Frame(tab_control)
        self.tab_sources = ttk.Frame(tab_control)
        
        tab_control.add(self.tab_control_panel, text='実行パネル')
        tab_control.add(self.tab_settings, text='移動先設定')
        tab_control.add(self.tab_sources, text='取得元設定')
        
        tab_control.pack(expand=1, fill="both")

        self.create_control_panel(self.tab_control_panel)
        self.create_settings_tab(self.tab_settings)
        self.create_sources_tab(self.tab_sources)

    def create_control_panel(self, parent):
        frame = ttk.Frame(parent, padding="10")
        frame.pack(fill="both", expand=True)

        # コントロール部分
        controls = ttk.LabelFrame(frame, text="操作", padding="10")
        controls.pack(fill="x", pady=5)

        # 即時実行ボタン
        self.btn_run_now = ttk.Button(controls, text="今すぐ実行", command=self.run_now)
        self.btn_run_now.pack(side="left", padx=5)

        # 定期実行設定
        ttk.Label(controls, text="実行間隔(分):").pack(side="left", padx=5)
        self.interval_var = tk.StringVar(value=str(self.config.get('interval', 3)))
        ttk.Entry(controls, textvariable=self.interval_var, width=5).pack(side="left")

        # バックグラウンド実行スイッチ
        self.btn_toggle_bg = ttk.Button(controls, text="定期実行を開始", command=self.toggle_background_task)
        self.btn_toggle_bg.pack(side="left", padx=5)

        self.lbl_status = ttk.Label(controls, text="待機中", foreground="gray")
        self.lbl_status.pack(side="left", padx=10)
        
        # 右寄せで終了ボタン
        self.btn_quit = ttk.Button(controls, text="アプリを終了", command=self.quit_app)
        self.btn_quit.pack(side="right", padx=5)

        # ログ表示エリア
        log_frame = ttk.LabelFrame(frame, text="実行ログ", padding="5")
        log_frame.pack(fill="both", expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', height=5)
        self.log_text.pack(fill="both", expand=True)

        # ステータスモニター
        monitor_frame = ttk.LabelFrame(frame, text="メール処理状況", padding="5")
        monitor_frame.pack(fill="both", expand=True, pady=5)

        columns = ('id', 'source', 'date', 'sender', 'subject', 'status')
        self.tree = ttk.Treeview(monitor_frame, columns=columns, show='headings', height=8)
        
        self.tree.heading('id', text='ID')
        self.tree.heading('source', text='取得元')
        self.tree.heading('date', text='日時')
        self.tree.heading('sender', text='送信者')
        self.tree.heading('subject', text='件名')
        self.tree.heading('status', text='状況')

        self.tree.column('id', width=50)
        self.tree.column('source', width=100)
        self.tree.column('date', width=120)
        self.tree.column('sender', width=120)
        self.tree.column('subject', width=200)
        self.tree.column('status', width=100)

        scrollbar = ttk.Scrollbar(monitor_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def update_status_callback(self, data):
        """
        コアロジックからのステータス更新を受け取るコールバック
        data: {
            'action': 'add' | 'update' | 'remove',
            'id': unique_id,
            'source': str,
            'date': str,
            'sender': str,
            'subject': str,
            'status': str
        }
        """
        self.root.after(0, self._process_status_update, data)

    def _process_status_update(self, data):
        action = data.get('action')
        uid = data.get('id')
        
        if action == 'add':
            values = (
                uid,
                data.get('source', ''),
                data.get('date', ''),
                data.get('sender', ''),
                data.get('subject', ''),
                data.get('status', '')
            )
            self.tree.insert('', 'end', iid=uid, values=values)
        
        elif action == 'update':
            if self.tree.exists(uid):
                self.tree.set(uid, 'status', data.get('status', ''))
        
        elif action == 'remove':
            if self.tree.exists(uid):
                self.tree.delete(uid)

    def create_settings_tab(self, parent):
        frame = ttk.Frame(parent, padding="10")
        frame.pack(fill="both", expand=True)

        dest = self.config.get('destination', {})

        self.dest_entries = {}
        fields = [
            ('ホスト', 'host', dest.get('host', '')),
            ('ポート', 'port', dest.get('port', 993)),
            ('ユーザー', 'user', dest.get('user', '')),
            ('パスワード', 'password', dest.get('password', '')),
            ('フォルダ', 'folder', dest.get('folder', 'INBOX')),
        ]

        for i, (label, key, val) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky='w', pady=2)
            if key == 'password':
                entry = ttk.Entry(frame, width=40, show='*')
            else:
                entry = ttk.Entry(frame, width=40)
            entry.insert(0, str(val))
            entry.grid(row=i, column=1, sticky='w', pady=2)
            self.dest_entries[key] = entry

        # SSL Checkbox
        self.dest_ssl_var = tk.BooleanVar(value=dest.get('ssl', True))
        ttk.Checkbutton(frame, text="SSL", variable=self.dest_ssl_var).grid(row=len(fields), column=1, sticky='w')

        ttk.Button(frame, text="設定を保存", command=self.save_destination_settings).grid(row=len(fields)+1, column=1, sticky='e', pady=10)

    def save_destination_settings(self):
        dest = {}
        for key, entry in self.dest_entries.items():
            val = entry.get()
            if key == 'port':
                try:
                    val = int(val)
                except ValueError:
                    messagebox.showerror("エラー", "Portは数値で入力してください")
                    return
            dest[key] = val
        dest['ssl'] = self.dest_ssl_var.get()
        
        self.config['destination'] = dest
        self.save_config()
        messagebox.showinfo("成功", "移動先設定を保存しました")

    def create_sources_tab(self, parent):
        frame = ttk.Frame(parent, padding="10")
        frame.pack(fill="both", expand=True)

        # リスト表示
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, side="left")

        self.source_listbox = tk.Listbox(list_frame, width=30, exportselection=False)
        self.source_listbox.pack(fill="both", expand=True)
        self.source_listbox.bind('<<ListboxSelect>>', self.on_source_select)

        self.refresh_source_list()

        # 編集エリア
        edit_frame = ttk.LabelFrame(frame, text="編集", padding="10")
        edit_frame.pack(fill="both", expand=True, side="right", padx=10)

        self.source_entries = {}
        fields = [
            ('プロトコル', 'protocol'),
            ('ホスト', 'host'),
            ('ポート', 'port'),
            ('ユーザー', 'user'),
            ('パスワード', 'password'),
            ('フォルダ', 'folder')
        ]
        
        for i, (label, key) in enumerate(fields):
            ttk.Label(edit_frame, text=label).grid(row=i, column=0, sticky='w', pady=2)
            if key == 'protocol':
                entry = ttk.Combobox(edit_frame, values=['pop3', 'imap'], width=37)
            elif key == 'password':
                entry = ttk.Entry(edit_frame, width=40, show='*')
            else:
                entry = ttk.Entry(edit_frame, width=40)
            entry.grid(row=i, column=1, sticky='w', pady=2)
            self.source_entries[key] = entry

        self.source_ssl_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(edit_frame, text="SSL", variable=self.source_ssl_var).grid(row=len(fields), column=1, sticky='w')

        self.source_delete_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(edit_frame, text="移動後に削除", variable=self.source_delete_var).grid(row=len(fields)+1, column=1, sticky='w')

        btn_frame = ttk.Frame(edit_frame)
        btn_frame.grid(row=len(fields)+2, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="新規追加", command=self.add_source).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="更新", command=self.update_source).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="削除", command=self.delete_source).pack(side="left", padx=5)

    def refresh_source_list(self):
        self.source_listbox.delete(0, tk.END)
        sources = self.config.get('sources', [])
        for src in sources:
            label = f"{src.get('user')} ({src.get('protocol')})"
            self.source_listbox.insert(tk.END, label)

    def get_source_from_entries(self):
        src = {}
        for key, entry in self.source_entries.items():
            val = entry.get()
            if key == 'port':
                try:
                    val = int(val)
                except ValueError:
                    return None
            src[key] = val
        src['ssl'] = self.source_ssl_var.get()
        src['delete_after_move'] = self.source_delete_var.get()
        return src

    def on_source_select(self, event):
        selection = self.source_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        src = self.config['sources'][index]

        for key, entry in self.source_entries.items():
            val = src.get(key, '')
            if isinstance(entry, ttk.Combobox):
                entry.set(str(val))
            else:
                entry.delete(0, tk.END)
                entry.insert(0, str(val))
        
        self.source_ssl_var.set(src.get('ssl', True))
        self.source_delete_var.set(src.get('delete_after_move', False))

    def add_source(self):
        src = self.get_source_from_entries()
        if src:
            if 'sources' not in self.config:
                self.config['sources'] = []
            self.config['sources'].append(src)
            self.save_config()
            self.refresh_source_list()
            messagebox.showinfo("成功", "追加しました")
        else:
            messagebox.showerror("エラー", "入力値が不正です")

    def update_source(self):
        selection = self.source_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "更新する項目を選択してください")
            return
        index = selection[0]
        
        src = self.get_source_from_entries()
        if src:
            self.config['sources'][index] = src
            self.save_config()
            self.refresh_source_list()
            messagebox.showinfo("成功", "更新しました")
        else:
            messagebox.showerror("エラー", "入力値が不正です")

    def delete_source(self):
        selection = self.source_listbox.curselection()
        if not selection:
            return
        if messagebox.askyesno("確認", "本当に削除しますか？"):
            index = selection[0]
            del self.config['sources'][index]
            self.save_config()
            self.refresh_source_list()
            # エントリクリア
            for entry in self.source_entries.values():
                entry.delete(0, tk.END)

    def setup_logging(self):
        self.log_queue = queue.Queue()
        handler = QueueHandler(self.log_queue)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
        
        # Start GUI update loop
        self.gui_log_handler = GuiLogHandler(self.log_text, self.log_queue)

    def run_now(self):
        if self.is_running_now:
            return
        
        self.btn_run_now.config(state='disabled')
        threading.Thread(target=self._run_task, daemon=True).start()

    @property
    def is_running_now(self):
        return self.btn_run_now['state'] == 'disabled'

    def _run_task(self):
        try:
            logging.info("=== 手動実行開始 ===")
            run_batch(self.config, self.stop_event, self.update_status_callback)
        except Exception as e:
            logging.error(f"実行エラー: {e}")
        finally:
            logging.info("=== 実行終了 ===")
            self.root.after(0, lambda: self.btn_run_now.config(state='normal'))

    def toggle_background_task(self):
        if self.is_running:
            # 停止処理
            logging.info("停止シグナルを送信中...")
            self.stop_event.set()
            # ボタンを一時的に無効化（連打防止）
            self.btn_toggle_bg.config(state='disabled')
            
            # スレッドが終了するのを待つわけにはいかない（ブロックするから）
            # UIの更新は _background_loop の finally ブロックまたは _reset_ui_state で行う
            
            # ただし、即座に見た目を変えたい場合はここでも変えるが、
            # 完全に停止したことを確認してから戻すのが安全。
            # ここでは「停止中...」にしておく
            self.btn_toggle_bg.config(text="停止処理中...")
            self.is_background_running = False
        else:
            # 開始処理
            try:
                interval = int(self.interval_var.get())
                if interval <= 0: raise ValueError
                
                # 設定に保存
                self.config['interval'] = interval
                self.save_config()
                
            except ValueError:
                messagebox.showerror("エラー", "実行間隔は正の整数(分)で入力してください")
                return

            self.is_running = True
            self.is_background_running = True
            self.stop_event.clear()
            self.btn_toggle_bg.config(text="定期実行を停止")
            self.lbl_status.config(text=f"実行中 (間隔: {interval}分)", foreground="green")
            
            self.bg_thread = threading.Thread(target=self._background_loop, args=(interval,), daemon=True)
            self.bg_thread.start()
            logging.info(f"定期実行を開始しました (間隔: {interval}分)")
        
        # トレイメニューを更新
        if TRAY_AVAILABLE and self.tray_icon:
            self.tray_icon.update_menu()

    def _background_loop(self, interval_minutes):
        try:
            while not self.stop_event.is_set():
                try:
                    logging.info("=== 定期実行開始 ===")
                    run_batch(self.config, self.stop_event, self.update_status_callback)
                except Exception as e:
                    logging.error(f"定期実行エラー: {e}")
                
                if self.stop_event.is_set():
                    break

                logging.info(f"次回実行まで待機中... ({interval_minutes}分)")
                
                # interval分待機 (1秒ごとにstopフラグチェック)
                for _ in range(interval_minutes * 60):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)
        finally:
            # スレッド終了時にUIをリセット
            self.root.after(0, self._reset_ui_state)

    def _reset_ui_state(self):
        self.is_running = False
        self.is_background_running = False
        self.stop_event.clear() # 次回のためにクリア
        self.btn_toggle_bg.config(text="定期実行を開始", state='normal')
        self.lbl_status.config(text="停止中", foreground="red")
        logging.info("定期実行が完全に停止しました")
        
        # トレイメニューを更新
        if TRAY_AVAILABLE and self.tray_icon:
            self.tray_icon.update_menu()
    
    def show_window(self):
        """ウィンドウを表示（トレイから復帰）"""
        self.root.deiconify()
        self.root.state('normal')
        self.root.lift()
        self.root.focus_force()
    
    def hide_window(self):
        """ウィンドウを非表示（トレイに格納）"""
        self.root.withdraw()
    
    def quit_app(self):
        """アプリケーションを完全に終了"""
        if self.is_running:
            self.stop_event.set()
        
        # PIDファイルを削除
        PIDManager.remove_pid()
        
        # トレイアイコンを停止
        if TRAY_AVAILABLE and self.tray_icon:
            self.tray_icon.stop()
        
        self.root.quit()
        self.root.destroy()


