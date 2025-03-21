"""
ユーティリティ関数を提供するモジュール
"""
import re
import urllib.parse

def get_product_id(url):
    """URLから商品IDを抽出する"""
    # Amazonの場合
    if "amazon.co.jp" in url:
        # /dp/XXXXXXXXX/ 形式のIDを抽出
        amazon_match = re.search(r'/dp/([A-Z0-9]{10})/?', url)
        if amazon_match:
            return amazon_match.group(1)
    
    # 楽天の場合
    elif "rakuten.co.jp" in url:
        # 商品IDの抽出ロジック（実際のURLパターンに合わせて調整）
        rakuten_match = re.search(r'item/([^/]+)', url)
        if rakuten_match:
            return rakuten_match.group(1)
    
    # IDが見つからない場合はURL全体をエンコード
    return urllib.parse.quote(url)

def generate_site_url(item):
    """商品の自サイトURLを生成する"""
    # サイトのドメイン（実際のドメインに置き換える）
    domain = "doronpa530.github.io/deal-tracker"
    
    # 商品IDを取得
    product_id = get_product_id(item.url)
    
    # サイト種別（amazon/rakuten）とIDからURLを生成
    return f"https://{domain}/products/{item.site}/{product_id}"

def format_notification_message(item, current_price, discount, buy_score):
    """通知メッセージを生成する（自サイト経由形式）"""
    site_url = generate_site_url(item)
    
    # 通知メッセージを作成（自サイト経由形式）
    message = (
        f"【セール速報】{item.name}が{discount}%オフの{current_price}円になっています！"
        f"(買い時スコア: {buy_score}/100)\n"
        f"詳細・価格推移はこちら👇\n"
        f"{site_url}"
    )
    
    return message