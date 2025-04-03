import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask import Flask, render_template, request, redirect, url_for, flash
from scraper.db_models import Session, Item, PriceHistory, Notification, init_db
from admin_routes import admin_required
import os
from datetime import datetime
import logging

# --- app.pyの修正 ---

# ロギング設定部分を以下のように修正
# 既存のロギング設定を削除し、以下に置き換え
if not logging.getLogger('werkzeug').handlers:
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # ハンドラの重複を避けるために既存のハンドラをクリア
    if logger.handlers:
        logger.handlers.clear()
    
    # ファイルハンドラとストリームハンドラを追加
    file_handler = logging.FileHandler(os.path.join(log_dir, 'app.log'))
    stream_handler = logging.StreamHandler()
    
    # フォーマットを設定
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    
    # ハンドラを追加
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# アプリケーション初期化
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-deal-tracker')

# 開発環境か本番環境かを判定
if 'PYTHONANYWHERE_DOMAIN' in os.environ:
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False
else:
    # 環境変数の読み込み（ローカル開発環境用）
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    app.config['ENV'] = 'development'
    app.config['DEBUG'] = True

# データベース初期化
try:
    init_db()
    logger.info("データベースが初期化されました")
except Exception as e:
    logger.error(f"データベース初期化エラー: {e}")

# ルート設定
@app.route('/')
def home():
    session = Session()
    try:
        # 最新の商品を取得（上位10件）
        products = session.query(Item).order_by(Item.updated_at.desc()).limit(10).all()
        return render_template('index.html', 
                              title='値下げスカウター', 
                              products=products)
    except Exception as e:
        logger.error(f"ホームページ表示エラー: {e}")
        return render_template('index.html', 
                              title='値下げスカウター', 
                              products=[])
    finally:
        session.close()

@app.route('/admin')
def admin_redirect():
    return redirect(url_for('admin.dashboard'))



@app.route('/amazon/', endpoint="amazon")
def amazon():
    session = Session()
    try:
        products = session.query(Item).filter_by(site='amazon').order_by(Item.updated_at.desc()).limit(20).all()
        return render_template('amazon/index.html', products=products, title='Amazon特価情報')  # 'templates/' を削除
    except Exception as e:
        logger.error(f"Amazon特価ページ表示エラー: {e}")
        return render_template('amazon/index.html', products=[], title='Amazon特価情報')  # 'templates/' を削除
    finally:
        session.close()

@app.route('/rakuten/', endpoint="rakuten")
def rakuten():
    session = Session()
    try:
        products = session.query(Item).filter_by(site='rakuten').order_by(Item.updated_at.desc()).limit(20).all()
        return render_template('rakuten/index.html', products=products, title='楽天特価情報')  # 'templates/' を削除
    except Exception as e:
        logger.error(f"楽天特価ページ表示エラー: {e}")
        return render_template('rakuten/index.html', products=[], title='楽天特価情報')  # 'templates/' を削除
    finally:
        session.close()

@app.route('/about/')
def about():
    return render_template('about.html', title='サイトについて')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    session = Session()
    try:
        if query:
            # 検索クエリがある場合、商品を検索
            products = session.query(Item).filter(
                Item.name.like(f'%{query}%')
            ).order_by(Item.updated_at.desc()).limit(20).all()
        else:
            # 検索クエリがない場合、空のリストを返す
            products = []
        
        return render_template('search_results.html', 
                              title=f'"{query}" の検索結果',
                              query=query,
                              products=products)
    except Exception as e:
        logger.error(f"検索エラー: {e}")
        return render_template('search_results.html',
                              title='検索結果',
                              query=query,
                              products=[])
    finally:
        session.close()

@app.route('/advanced_search')
def advanced_search():
    # カテゴリー一覧を取得
    session = Session()
    try:
        categories = []  # 本来はデータベースからカテゴリー一覧を取得
        return render_template('advanced_search.html', 
                              title='詳細検索',
                              categories=categories,
                              category_id=request.args.get('category'),
                              platform=request.args.get('platform'))
    except Exception as e:
        logger.error(f"詳細検索ページ表示エラー: {e}")
        return render_template('advanced_search.html',
                              title='詳細検索',
                              categories=[],
                              category_id=None,
                              platform=None)
    finally:
        session.close()

# エラーハンドラ
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', title='ページが見つかりません'), 404

# 管理者ルートの追加
from admin_routes import admin_bp
app.register_blueprint(admin_bp)


# スクレイパー管理関連のルート
# 元々 scraper_admin.py にあった内容をここに移植

# スクレイパー設定ファイルのパス
SCRAPER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'scraper', 'scraper_config.json')

# スクレイパーの実行状態を管理
scraper_status = {
    'amazon': 'stopped',  # stopped, running, error, completed
    'rakuten': 'stopped',
    'last_run': None,
    'errors': []
}

# スクレイパー設定の読み込み
def load_scraper_config():
    if os.path.exists(SCRAPER_CONFIG_PATH):
        with open(SCRAPER_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # デフォルト設定
        default_config = {
            'check_interval': 3,  # 時間
            'discount_threshold': 20,  # %
            'user_agents': {
                'amazon': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                'rakuten': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
            },
            'request_delay': {
                'amazon': 3,  # 秒
                'rakuten': 3  # 秒
            },
            'active_hours': {
                'start': 8,  # 8:00
                'end': 22    # 22:00
            },
            'active_sites': {
                'amazon': True,
                'rakuten': False
            }
        }
        # デフォルト設定を保存
        os.makedirs(os.path.dirname(SCRAPER_CONFIG_PATH), exist_ok=True)
        with open(SCRAPER_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        return default_config

# スクレイパー設定の保存
def save_scraper_config(config):
    with open(SCRAPER_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# スクレイパーダッシュボード
@app.route('/admin/scraper/')
@admin_required
def scraper_dashboard():
    # 基本統計情報
    stats = {
        'item_count': 0,
        'active_item_count': 0,
        'price_history_count': 0,
        'notification_count': 0,
        'amazon_count': 0,
        'rakuten_count': 0
    }
    
    # 現在の設定
    config = load_scraper_config()
    
    return render_template('admin/scraper/dashboard.html',
                          stats=stats,
                          recent_prices=[],
                          config=config,
                          status=scraper_status)

# スクレイパー設定画面
@app.route('/admin/scraper/settings', methods=['GET', 'POST'])
@admin_required
def scraper_settings():
    if request.method == 'POST':
        # フォームからの設定を取得して保存
        config = load_scraper_config()
        
        # 基本設定
        config['check_interval'] = int(request.form.get('check_interval', 3))
        config['discount_threshold'] = int(request.form.get('discount_threshold', 20))
        
        # ユーザーエージェント
        config['user_agents']['amazon'] = request.form.get('amazon_user_agent', config['user_agents']['amazon'])
        config['user_agents']['rakuten'] = request.form.get('rakuten_user_agent', config['user_agents']['rakuten'])
        
        # リクエスト遅延
        config['request_delay']['amazon'] = int(request.form.get('amazon_delay', 3))
        config['request_delay']['rakuten'] = int(request.form.get('rakuten_delay', 3))
        
        # 動作時間
        config['active_hours']['start'] = int(request.form.get('active_start', 8))
        config['active_hours']['end'] = int(request.form.get('active_end', 22))
        
        # アクティブサイト
        config['active_sites']['amazon'] = 'amazon_active' in request.form
        config['active_sites']['rakuten'] = 'rakuten_active' in request.form
        
        # 設定を保存
        save_scraper_config(config)
        flash('スクレイパー設定を保存しました', 'success')
        return redirect(url_for('scraper_settings'))
    
    # 現在の設定を読み込んで表示
    config = load_scraper_config()
    return render_template('admin/scraper/settings.html', config=config)

# スクレイパー手動実行
@app.route('/admin/scraper/run', methods=['POST'])
@admin_required
def run_scraper():
    site = request.form.get('site', 'all')
    
    # すでに実行中の場合はエラー
    if scraper_status.get(site) == 'running':
        flash('スクレイパーはすでに実行中です', 'warning')
        return redirect(url_for('scraper_dashboard'))
    
    # 状態を実行中に更新
    scraper_status[site] = 'running'
    scraper_status['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    flash(f'{site}のスクレイパーを開始しました', 'success')
    return redirect(url_for('scraper_dashboard'))

# スクレイパー停止
@app.route('/admin/scraper/stop', methods=['POST'])
@admin_required
def stop_scraper():
    site = request.form.get('site', 'all')
    
    # 実行中でない場合は何もしない
    if scraper_status.get(site) != 'running':
        flash('スクレイパーは実行中ではありません', 'warning')
        return redirect(url_for('scraper_dashboard'))
    
    # 状態を停止に更新
    scraper_status[site] = 'stopped'
    
    flash(f'{site}のスクレイパーを停止しました', 'success')
    return redirect(url_for('scraper_dashboard'))

# スクレイパーステータスのAPI
@app.route('/admin/scraper/status')
@admin_required
def get_scraper_status():
    return jsonify(scraper_status)

# --- app.pyの最下部 ---

# メインエントリポイント
if __name__ == '__main__':
    # 環境変数からデバッグモードを取得（なければデフォルトでFalse）
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    # デバッグモードが明示的に有効になっていない場合は無効にする
    if not debug_mode:
        app.logger.setLevel(logging.INFO)
        app.logger.handlers = logger.handlers  # ロガーのハンドラを共有
    
    app.run(debug=debug_mode, use_reloader=debug_mode)