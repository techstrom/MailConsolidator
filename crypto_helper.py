"""
パスワード暗号化ヘルパーモジュール

Fernet対称暗号化を使用してパスワードを暗号化/復号化します。
マスターキーは ~/.mailconsolidator/master.key に保存されます。
"""

from cryptography.fernet import Fernet, InvalidToken
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PasswordCrypto:
    """パスワード暗号化/復号化クラス"""
    
    def __init__(self):
        self.key_file = Path.home() / '.mailconsolidator' / 'master.key'
        self.key = self._load_or_create_key()
        self.fernet = Fernet(self.key)
    
    def _load_or_create_key(self) -> bytes:
        """
        マスターキーをロードまたは生成する
        
        Returns:
            bytes: マスターキー
        """
        if self.key_file.exists():
            logger.info(f"マスターキーを読み込みました: {self.key_file}")
            return self.key_file.read_bytes()
        else:
            logger.info("マスターキーが見つかりません。新しいキーを生成します。")
            return self._create_key()
    
    def _create_key(self) -> bytes:
        """
        新しいマスターキーを生成して保存する
        
        Returns:
            bytes: 生成されたマスターキー
        """
        key = Fernet.generate_key()
        
        # ディレクトリを作成
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        
        # キーファイルを保存
        self.key_file.write_bytes(key)
        
        # Windows環境でも動作するように権限設定を試みる
        try:
            os.chmod(self.key_file, 0o600)  # 所有者のみ読み書き可能
            logger.info(f"マスターキーを生成しました: {self.key_file} (権限: 600)")
        except Exception as e:
            logger.warning(f"ファイル権限の設定に失敗しました: {e}")
            logger.info(f"マスターキーを生成しました: {self.key_file}")
        
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        パスワードを暗号化する
        
        Args:
            plaintext: 平文パスワード
        
        Returns:
            str: Base64エンコードされた暗号文
        """
        if not plaintext:
            return ""
        
        try:
            encrypted = self.fernet.encrypt(plaintext.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"暗号化に失敗しました: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        パスワードを復号化する
        
        Args:
            ciphertext: Base64エンコードされた暗号文
        
        Returns:
            str: 平文パスワード
        
        Raises:
            InvalidToken: 復号化に失敗した場合
        """
        if not ciphertext:
            return ""
        
        try:
            decrypted = self.fernet.decrypt(ciphertext.encode('utf-8'))
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.error("復号化に失敗しました。マスターキーが正しくない可能性があります。")
            raise
        except Exception as e:
            logger.error(f"復号化エラー: {e}")
            raise
    
    def is_encrypted(self, text: str) -> bool:
        """
        文字列が暗号化されているかチェックする
        
        Fernetの暗号文は'gAAAAA'で始まるBase64文字列
        
        Args:
            text: チェックする文字列
        
        Returns:
            bool: 暗号化されている場合True
        """
        if not text:
            return False
        
        # Fernetの暗号文は'gAAAAA'で始まる
        return text.startswith('gAAAAA')
