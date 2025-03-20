# プロジェクト構造

\\\
deal-tracker/
 .github/
    workflows/
        docs.yml        # GitHub Pagesのデプロイ設定
 docs/
    _config.yml        # GitHub Pages設定
    index.md           # ドキュメントトップページ
    specs.md           # 設計書
    progress.md        # 進捗管理
    structure.md       # このファイル（プロジェクト構造）
 scraper/
    requirements.txt   # Pythonパッケージ依存関係
    scraper.py         # スクレイピングメインコード
    twitter_bot.py     # Twitter連携コード
 website/               # まだ未実装
 venv/                  # Python仮想環境（Gitでは追跡されていない）
 price_history.json     # スクレイピング結果の保存先
 README.md              # プロジェクト概要
\\\

## 開発環境情報

- Python 3.13.1
- 仮想環境: venv (プロジェクトルート直下の venv/ フォルダ)
- 主要パッケージ: requests, beautifulsoup4, pandas, tweepy, schedule
- VS Code でコード編集
- Git/GitHub で管理
