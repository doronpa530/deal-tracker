from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime
import logging
import os
from scraper.db_models import Session, Item, PriceHistory, Notification
import config

# ロガー設定
logger = logging.getLogger(__name__)

# 管理者ブループリント作成
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 管理者認証デコレータ
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('管理者ログインが必要です', 'danger')
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ログイン画面
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 環境変数またはconfigから認証情報を取得
        admin_username = config.ADMIN_USERNAME
        admin_password = config.ADMIN_PASSWORD
        
        if username == admin_username and password == admin_password:
            session['admin_logged_in'] = True
            flash('ログインしました', 'success')
            next_page = request.args.get('next', url_for('admin.dashboard'))
            return redirect(next_page)
        else:
            flash('ユーザー名またはパスワードが間違っています', 'danger')
    
    return render_template('admin/login.html')

# ダッシュボード
@admin_bp.route('/')
@admin_required
def dashboard():
    db_session = Session()
    try:
        # 基本統計情報の取得
        item_count = db_session.query(Item).count()
        active_item_count = db_session.query(Item).filter_by(active=True).count()
        price_history_count = db_session.query(PriceHistory).count()
        notification_count = db_session.query(Notification).count()
        
        # サイト別の商品数
        amazon_count = db_session.query(Item).filter_by(site='amazon').count()
        rakuten_count = db_session.query(Item).filter_by(site='rakuten').count()
        
        logger.info(f"管理ダッシュボードにアクセスしました: 商品数={item_count}")
        
        return render_template('admin/index.html',
                              now=datetime.now(),
                              stats={
                                  'item_count': item_count,
                                  'active_item_count': active_item_count,
                                  'price_history_count': price_history_count,
                                  'notification_count': notification_count,
                                  'amazon_count': amazon_count,
                                  'rakuten_count': rakuten_count
                              })
    except Exception as e:
        logger.error(f"ダッシュボード表示エラー: {e}")
        flash('データベースからの情報取得中にエラーが発生しました', 'danger')
        return render_template('admin/index.html',
                              now=datetime.now(),
                              stats={
                                  'item_count': 0,
                                  'active_item_count': 0,
                                  'price_history_count': 0,
                                  'notification_count': 0,
                                  'amazon_count': 0,
                                  'rakuten_count': 0
                              })
    finally:
        db_session.close()

# スクレイパー管理
@admin_bp.route('/scraper')
@admin_required
def scraper_dashboard():
    return render_template('admin/scraper/dashboard.html')

# スクレイパー設定
@admin_bp.route('/scraper/settings')
@admin_required
def scraper_settings():
    return render_template('admin/scraper/settings.html')

# Twitter管理
@admin_bp.route('/twitter')
@admin_required
def twitter_dashboard():
    return render_template('admin/twitter/dashboard.html')

# Twitter設定
@admin_bp.route('/twitter/settings')
@admin_required
def twitter_settings():
    return render_template('admin/twitter/settings.html')

# ログアウト
@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('ログアウトしました', 'success')
    return redirect(url_for('admin.login'))