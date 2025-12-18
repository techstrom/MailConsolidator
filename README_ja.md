# MailConsolidator

[日本語版 (Japanese)](README_ja.md) | [English](README_en.md)

MailConsolidator は、複数のメールアカウント（POP3 / IMAP）からメールを取得し、1 つの転送先 IMAP サーバに集約するための Python アプリケーションです。

## Why MailConsolidator（なぜ MailConsolidator なのか）

Google は、**2026 年 1 月以降**、Gmail の設定にある **「他のアカウントでメールを確認（Check mail from other accounts）」** 機能を通じた、POP を用いた外部メールアカウントからのメール取得をサポートしないことを発表しています。

この変更により、これまで Gmail に外部の POP メールを自動取得させ、1 つの受信箱で管理していたユーザの運用に影響が生じます。

MailConsolidator は、このギャップを補うことを目的として設計されています。Gmail の内蔵 POP 取得機能に依存するのではなく、MailConsolidator 自身が取得元メールサーバ（POP3 または IMAP）からメールを取得し、転送先の IMAP サーバ（Gmail を含む）へアップロードします。

これにより、以下を実現します。

* Gmail の POP 取得廃止後も、従来の「メール集約」運用を継続
* メール取得・削除・実行間隔を明示的に制御
* 特定のメールプロバイダに依存しない、標準プロトコル（POP3 / IMAP）ベースの構成

## 概要

MailConsolidator は、複数のメールサーバからメールを取得し、指定した IMAP サーバへ転送することで、メールを一元管理するためのツールです。GUI とコマンドラインの両方に対応しており、定期実行による自動処理も可能です。

## 主な機能

* **複数プロトコル対応**: POP3 / IMAP の両方に対応
* **未読メールのみ取得（IMAP）**: IMAP では未読メールのみを効率的に取得
* **定期実行**: 指定した間隔（分単位）で自動実行
* **リアルタイムモニタリング**: GUI 上で処理状況をリアルタイム表示
* **システムトレイ常駐（Windows）**: バックグラウンド動作に対応
* **単一インスタンス制御**: 起動済みの場合は既存 GUI を前面表示
* **取得後の保持／削除設定**: 取得元サーバ上のメール削除有無を選択可能
* **SSL/TLS 対応**: 安全な通信をサポート
* **Windows インストーラー提供**: 簡単に導入可能

## 動作要件

* Python 3.7 以降
* PyYAML
* psutil
* cryptography
* pystray（Windows システムトレイ用）
* Pillow（画像処理）
* certifi（SSL 証明書）

## インストール

### Windows ユーザー向け（推奨）

1. **インストーラーをダウンロード**

   * GitHub Releases から `MailConsolidator-Setup-1.0.0.exe` を取得

2. **インストーラーを実行**

   * ダブルクリックしてウィザードに従ってインストール

3. **起動**

   * スタートメニューまたはデスクトップアイコンから起動

### 開発者向け（ソースから実行）

```bash
git clone <repository-url>
cd MailConsolidator
pip install -r requirements.txt
python main.py
```

## 使い方

### GUI モード

```bash
python main.py
```

すでに起動している場合、新しいプロセスは起動せず、既存の GUI ウィンドウが前面に表示されます。

#### GUI 操作概要

* **転送先設定**: 転送先 IMAP サーバ情報を入力して保存
* **取得元設定**: POP3 / IMAP アカウントを複数登録可能
* **実行パネル**:

  * 今すぐ実行
  * 定期実行の開始／停止
  * アプリ終了

### 起動モード

* 通常起動（バックグラウンド）
* 詳細ログ付き起動（`-v`）
* デーモンモード（GUI なし、`-d`）

## Gmail 利用時の注意

### Gmail の POP 取得について

Gmail では、2026 年 1 月以降、外部アカウントから POP を用いてメールを取得する機能が提供されなくなります。本ツールは、その代替手段としての利用を想定しています。

### Gmail アプリパスワード

2 段階認証を有効にしている Gmail アカウントでは、通常のパスワードではなく **アプリパスワード** を使用してください。

### Gmail IMAP 設定

* IMAP 有効化（Gmail 設定 → メール転送と POP/IMAP）
* ホスト: `imap.gmail.com`
* ポート: `993`
* SSL/TLS: 有効

## 設定ファイル

### 保存場所

* **Windows**: `%APPDATA%\MailConsolidator\config.yaml`
* **Unix 系**: `~/.config/MailConsolidator/config.yaml`

## ライセンス

本プロジェクトは [MIT ライセンス](./LICENSE) のもとで公開されています。

## 注意事項

* 設定ファイルには暗号化されたパスワードが含まれます。ファイルのアクセス権限に注意してください。
* 初回実行時や大量のメールを処理する場合、時間がかかることがあります。
* メールサーバの接続数制限にご注意ください。
