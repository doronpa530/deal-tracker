from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from dotenv import load_dotenv
import os

# .env ファイルを読み込む
load_dotenv()

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
        
        # 環境変数から認証情報を取得
        admin_username = os.environ.get('ADMIN_USERNAME')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        
        # 認証処理
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
    return render_template('admin/index.html')

# ログアウト
@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('ログアウトしました', 'success')
    return redirect(url_for('admin.login'))