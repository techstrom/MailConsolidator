import logging
import threading
import email
from email.header import decode_header
from typing import Dict, Any, Optional, Callable
from mail_client import Pop3Source, ImapSource, ImapDestination

logger = logging.getLogger(__name__)

def decode_str(s):
    """メールヘッダのデコード処理"""
    if s:
        decoded_list = decode_header(s)
        result = ""
        for decoded, charset in decoded_list:
            if isinstance(decoded, bytes):
                if charset:
                    try:
                        result += decoded.decode(charset)
                    except LookupError:
                        result += decoded.decode('utf-8', errors='replace')
                    except Exception:
                        result += decoded.decode('utf-8', errors='replace')
                else:
                    result += decoded.decode('utf-8', errors='replace')
            else:
                result += str(decoded)
        return result
    return ""

def run_batch(config: Dict[str, Any], stop_event: Optional[threading.Event] = None, callback: Optional[Callable] = None) -> str:
    """
    設定に基づいて一括処理を実行する
    戻り値: 実行結果のサマリ文字列
    """
    # 移動先の設定
    dest_config = config.get('destination')
    if not dest_config:
        raise ValueError("移動先(destination)の設定が見つかりません")

    destination = ImapDestination(dest_config)
    
    try:
        destination.connect()
    except Exception as e:
        logger.error(f"移動先サーバへの接続に失敗しました: {e}")
        raise e

    total_moved = 0
    total_errors = 0
    
    try:
        # 各ソースアカウントを処理
        sources = config.get('sources', [])
        for source_config in sources:
            if stop_event and stop_event.is_set():
                logger.info("停止シグナルを検知しました。処理を中断します。")
                break
                
            try:
                moved = process_source(source_config, destination, stop_event, callback)
                total_moved += moved
            except Exception as e:
                logger.error(f"ソース処理エラー: {e}")
                total_errors += 1
            
    finally:
        destination.disconnect()
        
    return f"処理完了: 合計 {total_moved} 通移動しました (エラー: {total_errors} 件)"

def process_source(source_config: Dict[str, Any], destination: ImapDestination, stop_event: Optional[threading.Event] = None, callback: Optional[Callable] = None) -> int:
    """
    1つのソースアカウントを処理する
    戻り値: 移動したメッセージ数
    """
    protocol = source_config.get('protocol', '').lower()
    host = source_config.get('host')
    user = source_config.get('user')
    
    logger.info(f"--- アカウント処理開始: {user} ({protocol}://{host}) ---")

    source = None
    if protocol == 'pop3':
        source = Pop3Source(source_config)
    elif protocol == 'imap':
        source = ImapSource(source_config)
    else:
        logger.error(f"未対応のプロトコルです: {protocol}")
        return 0

    moved_count = 0
    try:
        source.connect()
        messages = source.get_messages()
        
        if not messages:
            logger.info("新しいメッセージはありません")
            return 0

        logger.info(f"{len(messages)} 件のメッセージを移動します...")

        for msg_id, msg_bytes in messages:
            if stop_event and stop_event.is_set():
                logger.info("停止シグナルを検知しました。メッセージ移動を中断します。")
                break

            # ヘッダ解析
            msg_obj = email.message_from_bytes(msg_bytes)
            subject = decode_str(msg_obj.get('Subject'))
            sender = decode_str(msg_obj.get('From'))
            date = msg_obj.get('Date')
            
            # ユニークID生成 (簡易的)
            unique_id = f"{user}-{msg_id}"

            # GUI更新: 取得完了
            if callback:
                callback({
                    'action': 'add',
                    'id': unique_id,
                    'source': user,
                    'date': date,
                    'sender': sender,
                    'subject': subject,
                    'status': '取得完了'
                })

            # 移動先へアップロード
            if callback:
                callback({'action': 'update', 'id': unique_id, 'status': '保存中...'})
            
            if destination.append_message(msg_bytes):
                if callback:
                    callback({'action': 'update', 'id': unique_id, 'status': '保存完了'})

                # 成功したら、設定に応じて削除または既読マーク
                if source.delete_after_move:
                    # 削除する設定の場合
                    if callback:
                        callback({'action': 'update', 'id': unique_id, 'status': '削除中...'})
                    try:
                        source.delete_message(msg_id)
                        moved_count += 1
                        if callback:
                            callback({'action': 'update', 'id': unique_id, 'status': '削除完了'})
                    except Exception as e:
                        logger.error(f"メッセージ削除失敗 (ID: {msg_id}): {e}")
                        if callback:
                            callback({'action': 'update', 'id': unique_id, 'status': '削除失敗'})
                    
                    # 削除設定の場合のみリストから削除
                    if callback:
                        callback({'action': 'remove', 'id': unique_id})
                else:
                    # 削除しない設定の場合
                    moved_count += 1
                    
                    # IMAPの場合は既読マークを付ける
                    if isinstance(source, ImapSource):
                        if callback:
                            callback({'action': 'update', 'id': unique_id, 'status': '既読マーク中...'})
                        try:
                            source.mark_as_read(msg_id)
                            if callback:
                                callback({'action': 'update', 'id': unique_id, 'status': '完了（保持）'})
                        except Exception as e:
                            logger.error(f"既読マーク失敗 (ID: {msg_id}): {e}")
                            if callback:
                                callback({'action': 'update', 'id': unique_id, 'status': '完了（エラー）'})
                    else:
                        # POP3の場合は何もしない（サーバに残る）
                        if callback:
                            callback({'action': 'update', 'id': unique_id, 'status': '完了（保持）'})
                    
                    # リストから削除しない（保持）
            else:
                logger.warning(f"メッセージ移動失敗 (ID: {msg_id}) - 削除はスキップします")
                if callback:
                    callback({'action': 'update', 'id': unique_id, 'status': '移動失敗'})

        logger.info(f"処理完了: {moved_count}/{len(messages)} 件移動しました")

    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {e}")
        raise e
    finally:
        if source:
            source.disconnect()
            
    return moved_count
