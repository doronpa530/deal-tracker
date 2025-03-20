import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
import schedule
from datetime import datetime

# 設定ファイル
config = {
    "target_items": [
        {"name": "Amazon Echo Dot (第5世代)", "url": "https://www.amazon.co.jp/dp/B09ZX764ZL/", "normal_price": 5980},
        {"name": "Anker PowerCore", "url": "https://www.amazon.co.jp/dp/B01N0X3NL5/", "normal_price": 2990}
    ],
    # 他の設定は変更なし
    "discount_threshold": 20,
    "check_interval": 3,
    "twitter": {
        "api_key": "YOUR_API_KEY",
        "api_secret": "YOUR_API_SECRET",
        "access_token": "YOUR_ACCESS_TOKEN",
        "access_secret": "YOUR_ACCESS_SECRET"
    }
}

# データベース代わりのJSONファイル
DB_FILE = "price_history.json"

def load_database():
    """データベースを読み込む"""
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"items": {}, "notifications": []}

def save_database(db):
    """データベースを保存する"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_amazon_price(url):
    """Amazonの商品価格を取得する関数"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://www.google.com/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # レスポンスが正常でない場合はログ出力して終了
        if response.status_code != 200:
            print(f"HTTP エラー: {response.status_code}, URL: {url}")
            return None
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # デバッグ用にHTMLを保存（必要に応じてコメント解除）
        # with open(f"amazon_page_debug.html", "w", encoding="utf-8") as f:
        #     f.write(response.text)
        
        # 複数の価格要素セレクタを試す
        selectors = [
            ".a-price .a-offscreen",  # 通常価格表示
            "#priceblock_ourprice",  # 標準価格
            "#priceblock_dealprice",  # セール価格
            ".apexPriceToPay .a-offscreen",  # 新しい価格表示
            "#corePrice_feature_div .a-price .a-offscreen"  # コア価格要素
        ]
        
        # 価格テキスト取得のための試行
        price_text = None
        for selector in selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text(strip=True)
                print(f"価格テキスト発見: {price_text}")
                break
        
        # 価格テキストが見つからない場合
        if not price_text:
            print(f"価格要素が見つかりませんでした: {url}")
            return None
        
        # 価格テキストから数値だけ抽出
        import re
        # 通貨記号や区切り文字を除去
        price_clean = re.sub(r'[^\d.]', '', price_text)
        
        # 数値に変換
        try:
            price = int(float(price_clean))
            return price
        except ValueError:
            print(f"価格の変換に失敗しました: {price_text}")
            return None
            
    except Exception as e:
        print(f"Amazonの価格取得中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()  # スタックトレースを出力
        return None

def get_rakuten_price(url):
    """楽天の商品価格を取得する関数"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 価格取得（実際のサイトに合わせて調整が必要）
        price_element = soup.select_one(".price")
        if price_element:
            price_text = price_element.text.replace("円", "").replace(",", "").strip()
            return int(price_text)
        return None
    except Exception as e:
        print(f"Error getting Rakuten price: {e}")
        return None

def get_price(url):
    """URLに応じて適切な価格取得関数を呼び出す"""
    if "amazon.co.jp" in url:
        return get_amazon_price(url)
    elif "rakuten.co.jp" in url:
        return get_rakuten_price(url)
    return None

def calculate_discount(normal_price, current_price):
    """値引き率を計算"""
    if normal_price == 0:
        return 0
    return round((normal_price - current_price) / normal_price * 100)

def check_prices():
    """全ての対象商品の価格をチェックし、必要に応じて通知"""
    print(f"Checking prices at {datetime.now()}")
    db = load_database()
    
    for item in config["target_items"]:
        item_name = item["name"]
        item_url = item["url"]
        normal_price = item["normal_price"]
        
        current_price = get_price(item_url)
        if current_price is None:
            continue
            
        # 商品情報を更新
        if item_name not in db["items"]:
            db["items"][item_name] = {
                "url": item_url,
                "normal_price": normal_price,
                "price_history": []
            }
        
        db["items"][item_name]["price_history"].append({
            "timestamp": datetime.now().isoformat(),
            "price": current_price
        })
        
        # 履歴は最新10件だけ保持
        db["items"][item_name]["price_history"] = db["items"][item_name]["price_history"][-10:]
        
        # 割引率を計算
        discount = calculate_discount(normal_price, current_price)
        
        # 閾値以上の割引があれば通知
        if discount >= config["discount_threshold"]:
            message = f"【セール速報】{item_name}が{discount}%オフの{current_price}円になっています！\n{item_url}"
            print(message)
            
            # 前回の通知から24時間以上経過しているか確認
            last_notification = None
            for notification in db["notifications"]:
                if notification["item_name"] == item_name:
                    last_notification = notification
                    break
                    
            should_notify = True
            if last_notification:
                last_time = datetime.fromisoformat(last_notification["timestamp"])
                hours_passed = (datetime.now() - last_time).total_seconds() / 3600
                if hours_passed < 24:
                    should_notify = False
            
            if should_notify:
                # 通知処理（Twitter連携などは別ファイルに実装予定）
                db["notifications"].append({
                    "item_name": item_name,
                    "timestamp": datetime.now().isoformat(),
                    "message": message,
                    "price": current_price,
                    "discount": discount
                })
    
    # 通知履歴は最新20件だけ保持
    db["notifications"] = db["notifications"][-20:]
    
    # データベース保存
    save_database(db)

def main():
    # 初回実行
    check_prices()
    
    # 定期実行のスケジュール設定
    schedule.every(config["check_interval"]).hours.do(check_prices)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()