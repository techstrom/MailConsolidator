import threading
import os
from PIL import Image, ImageDraw, ImageFont
import pystray
from pystray import MenuItem as item


class SystemTrayIcon:
    """Windowsのシステムトレイアイコンを管理するクラス"""
    
    def __init__(self, app):
        """
        Args:
            app: MailConsolidatorAppインスタンス
        """
        self.app = app
        self.icon = None
        self.thread = None
        self.running = False
        
    def create_icon(self):
        """トレイアイコン用の画像を生成"""
        # 64x64の画像を作成
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # 背景を青色に
        draw.rectangle([0, 0, width, height], fill='#2196F3')
        
        # 白い封筒のアイコンを描画
        # 封筒の本体
        envelope_margin = 12
        draw.rectangle(
            [envelope_margin, envelope_margin + 8, width - envelope_margin, height - envelope_margin],
            fill='white',
            outline='#1976D2',
            width=2
        )
        
        # 封筒のフラップ（三角形）
        flap_points = [
            (envelope_margin, envelope_margin + 8),
            (width // 2, height // 2 - 4),
            (width - envelope_margin, envelope_margin + 8)
        ]
        draw.polygon(flap_points, fill='white', outline='#1976D2')
        draw.line(flap_points, fill='#1976D2', width=2)
        
        return image
    
    def create_menu(self):
        """トレイメニューを作成"""
        return pystray.Menu(
            item(
                'ウィンドウを表示/非表示',
                self.toggle_window,
                default=True
            ),
            pystray.Menu.SEPARATOR,
            item(
                lambda text: f'定期実行: {"ON" if self.app.is_background_running else "OFF"}',
                self.toggle_background,
                checked=lambda item: self.app.is_background_running
            ),
            pystray.Menu.SEPARATOR,
            item(
                '終了',
                self.quit_app
            )
        )
    
    def toggle_window(self, icon=None, item=None):
        """ウィンドウの表示/非表示を切り替え"""
        if self.app.root.state() == 'withdrawn':
            self.show_window()
        else:
            self.hide_window()
    
    def show_window(self, icon=None, item=None):
        """ウィンドウを表示"""
        self.app.root.after(0, self._show_window_impl)
    
    def _show_window_impl(self):
        """ウィンドウ表示の実装（メインスレッドで実行）"""
        self.app.root.deiconify()
        self.app.root.state('normal')
        self.app.root.lift()
        self.app.root.focus_force()
    
    def hide_window(self, icon=None, item=None):
        """ウィンドウを非表示（トレイに格納）"""
        self.app.root.after(0, self._hide_window_impl)
    
    def _hide_window_impl(self):
        """ウィンドウ非表示の実装（メインスレッドで実行）"""
        self.app.root.withdraw()
    
    def toggle_background(self, icon=None, item=None):
        """定期実行のオン/オフを切り替え"""
        self.app.root.after(0, self.app.toggle_background_task)
    
    def quit_app(self, icon=None, item=None):
        """アプリケーションを終了"""
        self.stop()
        self.app.root.after(0, self.app.quit_app)
    
    def run(self):
        """トレイアイコンを起動（別スレッドで実行）"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_icon, daemon=True)
        self.thread.start()
    
    def _run_icon(self):
        """トレイアイコンの実行ループ"""
        try:
            self.icon = pystray.Icon(
                'MailConsolidator',
                self.create_icon(),
                'MailConsolidator',
                self.create_menu()
            )
            self.icon.run()
        except Exception as e:
            print(f"トレイアイコンエラー: {e}")
    
    def stop(self):
        """トレイアイコンを停止"""
        if self.icon:
            self.icon.stop()
        self.running = False
    
    def update_menu(self):
        """メニューを更新（定期実行状態の変更を反映）"""
        if self.icon:
            self.icon.menu = self.create_menu()
            self.icon.update_menu()
