# セール情報通知サービス - ドキュメント

## 目次

- [仕様書](specs.md)
- [進捗状況](progress.md)

## 概要

このプロジェクトは、Amazon・楽天の特価情報を自動で収集し、Twitter等で通知するサービスです。

## クイックスタート

1. `scraper/requirements.txt` に記載されたパッケージをインストール
2. `scraper/scraper.py` の設定を編集
3. `python scraper/scraper.py` でスクレイパーを実行
4. 必要に応じて `python scraper/twitter_bot.py` でTwitter通知を送信ok
5. 開発環境のアクティベーション
   - Windows: .\venv\Scripts\activate

6. 変更をGitHubにプッシュ
   ```bash
   git add .
   git commit -m "変更内容の説明"
   git push origin main