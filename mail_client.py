import poplib
import imaplib
import email
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
import ssl
import ssl
# import certifi  <-- Removed top-level import to avoid ModuleNotFoundError in frozen app

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import sys
import os

# SSL証明書の設定（PyInstaller対応）
def create_ssl_context():
    """SSL/TLSコンテキストを作成（PyInstaller環境でも動作）"""
    # one-folderモードでは証明書検証を有効にできる
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # デフォルトの証明書検証を使用（システムの証明書ストア）
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    # システムのデフォルト証明書をロード
    context.load_default_certs()
    return context

class MailSource(ABC):
    """メール取得元の基底クラス"""
    def __init__(self, config: Dict[str, Any]):
        self.host = config['host']
        self.port = config['port']
        self.user = config['user']
        self.password = config['password']
        self.ssl = config.get('ssl', True)
        self.delete_after_move = config.get('delete_after_move', False)

    @abstractmethod
    def connect(self):
        """サーバに接続する"""
        pass

    @abstractmethod
    def disconnect(self):
        """サーバから切断する"""
        pass

    @abstractmethod
    def get_messages(self) -> List[bytes]:
        """メッセージのリスト（バイト列）を取得する"""
        pass

    @abstractmethod
    def delete_message(self, message_id: Any):
        """メッセージを削除する"""
        pass

class Pop3Source(MailSource):
    """POP3サーバからのメール取得クラス"""
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection = None

    def connect(self):
        logger.info(f"POP3サーバ {self.host}:{self.port} に接続中...")
        if self.ssl:
            context = create_ssl_context()
            self.connection = poplib.POP3_SSL(self.host, self.port, context=context)
        else:
            self.connection = poplib.POP3(self.host, self.port)
        self.connection.user(self.user)
        self.connection.pass_(self.password)
        logger.info("POP3接続成功")

    def disconnect(self):
        if self.connection:
            self.connection.quit()
            self.connection = None
            logger.info("POP3切断完了")

    def get_messages(self) -> List[tuple]:
        """
        メッセージを取得する。
        戻り値: (message_index, message_bytes) のリスト
        """
        if not self.connection:
            raise ConnectionError("接続されていません")

        num_messages = len(self.connection.list()[1])
        logger.info(f"{num_messages} 件のメッセージが見つかりました")
        
        messages = []
        # POP3は1-based index
        for i in range(1, num_messages + 1):
            try:
                # retrは (response, lines, octets) を返す
                response, lines, octets = self.connection.retr(i)
                message_bytes = b'\r\n'.join(lines)
                messages.append((i, message_bytes))
            except Exception as e:
                logger.error(f"メッセージ {i} の取得に失敗しました: {e}")
        
        return messages

    def delete_message(self, message_id: Any):
        """
        POP3での削除。message_idはメッセージ番号(int)。
        """
        if not self.connection:
            raise ConnectionError("接続されていません")
        self.connection.dele(message_id)
        logger.info(f"メッセージ {message_id} を削除マークしました")


class ImapSource(MailSource):
    """IMAPサーバからのメール取得クラス"""
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.folder = config.get('folder', 'INBOX')
        self.connection = None

    def connect(self):
        logger.info(f"IMAPサーバ {self.host}:{self.port} に接続中...")
        if self.ssl:
            context = create_ssl_context()
            self.connection = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=context)
        else:
            self.connection = imaplib.IMAP4(self.host, self.port)
        
        self.connection.login(self.user, self.password)
        self.connection.select(self.folder)
        logger.info(f"IMAP接続成功 (フォルダ: {self.folder})")

    def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
            self.connection.logout()
            self.connection = None
            logger.info("IMAP切断完了")

    def get_messages(self) -> List[tuple]:
        """
        メッセージを取得する。
        戻り値: (message_uid, message_bytes) のリスト
        """
        if not self.connection:
            raise ConnectionError("接続されていません")

        # 未読メッセージを検索
        typ, data = self.connection.search(None, 'UNSEEN')
        if typ != 'OK':
            logger.warning("メッセージの検索に失敗しました")
            return []

        message_ids = data[0].split()
        logger.info(f"{len(message_ids)} 件のメッセージが見つかりました")

        messages = []
        for num in message_ids:
            try:
                typ, msg_data = self.connection.fetch(num, '(RFC822)')
                if typ != 'OK':
                    continue
                
                # msg_data[0] は (header, body) のタプル、bodyがメッセージ本体
                message_bytes = msg_data[0][1]
                messages.append((num, message_bytes))
            except Exception as e:
                logger.error(f"メッセージ {num} の取得に失敗しました: {e}")
        
        return messages

    def mark_as_read(self, message_id: Any):
        """
        IMAPでメッセージを既読にマークする。message_idはメッセージ番号(bytes)。
        """
        if not self.connection:
            raise ConnectionError("接続されていません")
        
        self.connection.store(message_id, '+FLAGS', '\\Seen')
        logger.info(f"メッセージ {message_id} を既読にマークしました")

    def delete_message(self, message_id: Any):
        """
        IMAPでの削除。message_idはメッセージ番号(bytes)。
        Deletedフラグを立ててexpungeする。
        """
        if not self.connection:
            raise ConnectionError("接続されていません")
        
        self.connection.store(message_id, '+FLAGS', '\\Deleted')
        self.connection.expunge()
        logger.info(f"メッセージ {message_id} を削除しました")


class ImapDestination:
    """移動先IMAPサーバクラス"""
    def __init__(self, config: Dict[str, Any]):
        self.host = config['host']
        self.port = config['port']
        self.user = config['user']
        self.password = config['password']
        self.ssl = config.get('ssl', True)
        self.folder = config.get('folder', 'INBOX')
        self.connection = None

    def connect(self):
        logger.info(f"移動先IMAPサーバ {self.host}:{self.port} に接続中...")
        if self.ssl:
            context = create_ssl_context()
            self.connection = imaplib.IMAP4_SSL(self.host, self.port, ssl_context=context)
        else:
            self.connection = imaplib.IMAP4(self.host, self.port)
        
        self.connection.login(self.user, self.password)
        
        # フォルダが存在するか確認、なければ作成（オプション）
        # ここでは単純にselectする
        try:
            self.connection.select(self.folder)
        except imaplib.IMAP4.error:
            logger.warning(f"フォルダ {self.folder} が見つかりません。作成を試みます。")
            self.connection.create(self.folder)
            self.connection.select(self.folder)
            
        logger.info("移動先IMAP接続成功")

    def disconnect(self):
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
            self.connection.logout()
            self.connection = None
            logger.info("移動先IMAP切断完了")

    def append_message(self, message_bytes: bytes) -> bool:
        """
        メッセージをフォルダに追加する。
        """
        if not self.connection:
            raise ConnectionError("接続されていません")
        
        try:
            # append(mailbox, flags, date_time, message)
            # flagsとdate_timeはNoneでよい（現在時刻とデフォルトフラグ）
            self.connection.append(self.folder, None, None, message_bytes)
            return True
        except Exception as e:
            logger.error(f"メッセージのアップロードに失敗しました: {e}")
            return False
