import requests
from bs4 import BeautifulSoup
import time
import schedule
from datetime import datetime
import re
import os
from db_models import Session, Item, PriceHistory, Notification

# データベース内の初期商品リスト（既存アイテムがない場合のみ使用）
DEFAULT_ITEMS = [
    {
        "name": "Amazon Echo Dot (第5世代)",
        "url": "https://www.amazon.co.jp/dp/B09ZX764ZL/",
        "normal_price": 5980,
        "site": "amazon"
    },
    {
        "name": "Anker PowerCore",
        "url": "https://www.amazon.co.jp/dp/B01N0X3NL5/",
        "normal_price": 2990,
        "site": "amazon"
    }
]

# 設定
DISCOUNT_THRESHOLD = 20  # 20%以上値下げされたら通知
CHECK_INTERVAL = 3       # 3時間ごとにチェック

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
        
        # デバッグ用にHTMLを保存
        debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        with open(os.path.join(debug_dir, f"amazon_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"), "w", encoding="utf-8") as f:
            f.write(response.text)
        
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"HTTP エラー: {response.status_code}, URL: {url}")
            return None
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # デバッグ用にHTMLを保存
        debug_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        with open(os.path.join(debug_dir, f"rakuten_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"), "w", encoding="utf-8") as f:
            f.write(response.text)
            
        # 複数の価格要素セレクタを試す
        selectors = [
            ".price",  # 標準価格表示
            ".priceBox .price",  # 価格ボックス内
            "#priceCalculationConfig" # 価格計算設定（JSON）
        ]
        
        for selector in selectors:
            price_element = soup.select_one(selector)
            if price_element:
                # JSONデータの場合
                if selector == "#priceCalculationConfig":
                    try:
                        import json
                        price_data = json.loads(price_element.get("data-json"))
                        price = int(price_data.get("price", 0))
                        return price
                    except:
                        continue
                
                # 通常のテキスト要素の場合
                price_text = price_element.get_text(strip=True)
                price_clean = re.sub(r'[^\d]', '', price_text)
                try:
                    return int(price_clean)
                except ValueError:
                    continue
        
        print(f"楽天の価格が見つかりませんでした: {url}")
        return None
        
    except Exception as e:
        print(f"楽天の価格取得中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
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
    if normal_price == 0 or normal_price is None or current_price is None:
        return 0
    return round((normal_price - current_price) / normal_price * 100, 2)

def calculate_buy_score(item_id, current_price, normal_price):
    """買い時スコアを計算（0-100）"""
    # 基本スコア：現在の割引率に基づく（最大60点）
    discount = calculate_discount(normal_price, current_price)
    base_score = min(60, discount * 1.5)
    
    # 履歴スコア：過去の最安値との比較（最大40点）
    session = Session()
    try:
        # 過去の価格履歴を取得
        histories = session.query(PriceHistory).filter_by(item_id=item_id).all()
        
        if not histories:
            history_score = 40  # 履歴がない場合は満点
        else:
            # 過去最安値を取得
            min_price = min(h.price for h in histories)
            
            # 現在価格が過去最安値と同じかより安い場合は満点
            if current_price <= min_price:
                history_score = 40
            else:
                # 現在価格が過去最安値からどれだけ離れているか計算
                price_diff_percent = (current_price - min_price) / min_price * 100
                history_score = max(0, 40 - price_diff_percent)
    except Exception as e:
        print(f"履歴スコア計算エラー: {e}")
        history_score = 20  # エラー時は中間点
    finally:
        session.close()
    
    # 総合スコア（四捨五入して整数に）
    total_score = round(base_score + history_score)
    
    # 0-100の範囲に収める
    return max(0, min(100, total_score))

def check_prices():
    """全ての対象商品の価格をチェックし、必要に応じて通知"""
    print(f"価格チェック開始: {datetime.now()}")
    
    # データベースセッションを作成
    session = Session()
    
    try:
        # データベースから商品を取得
        items = session.query(Item).filter_by(active=True).all()
        
        # データベースに商品がなければ、デフォルト商品を作成
        if not items:
            print("データベースに商品がありません。デフォルト商品を作成します。")
            for item_data in DEFAULT_ITEMS:
                item = Item(
                    name=item_data["name"],
                    url=item_data["url"],
                    site=item_data["site"],
                    normal_price=item_data["normal_price"],
                    active=True
                )
                session.add(item)
            
            # 変更をコミット
            session.commit()
            
            # 再度商品を取得
            items = session.query(Item).filter_by(active=True).all()
        
        print(f"チェック対象商品数: {len(items)}")
        
        # 各商品の価格をチェック
        for item in items:
            print(f"商品をチェック中: {item.name}")
            current_price = get_price(item.url)
            
            if current_price is None:
                print(f"価格取得失敗: {item.name}")
                continue
            
            print(f"価格取得成功: {item.name} - {current_price}円")
            
            # 商品の現在価格を更新
            item.current_price = current_price
            item.updated_at = datetime.now()
            
            # 価格履歴を追加
            discount = calculate_discount(item.normal_price, current_price)
            price_history = PriceHistory(
                item_id=item.id,
                price=current_price,
                discount_rate=discount,
                timestamp=datetime.now()
            )
            session.add(price_history)
            
            # 閾値以上の割引があれば通知
            if discount >= DISCOUNT_THRESHOLD:
                # 買い時スコアを計算
                buy_score = calculate_buy_score(item.id, current_price, item.normal_price)
    
                 # 通知メッセージを作成（自サイト経由形式）
                message = format_notification_message(item, current_price, discount, buy_score)
                print(f"通知条件達成: {message}")
                
                # 前回の通知から24時間以上経過しているか確認
                last_notification = session.query(Notification)\
                    .filter_by(item_id=item.id)\
                    .order_by(Notification.timestamp.desc())\
                    .first()
    
                should_notify = True
                if last_notification:
                    hours_passed = (datetime.now() - last_notification.timestamp).total_seconds() / 3600
                    if hours_passed < 24:
                        print(f"前回の通知から24時間経過していないためスキップ: {hours_passed}時間")
                        should_notify = False
                
                if should_notify:
                    # 通知を作成
                    notification = Notification(
                        item_id=item.id,
                        price=current_price,
                        discount_rate=discount,
                        buy_score=buy_score,
                        message=message,
                        tweeted=False,
                        timestamp=datetime.now()
                    )
                    session.add(notification)
                    print(f"通知を作成しました: {item.name}")
        
        # 変更をコミット
        session.commit()
        print("価格チェック完了、データベースを更新しました。")
    
    except Exception as e:
        session.rollback()
        print(f"価格チェック中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

def main():
    """メイン実行関数"""
    print("価格追跡システムを開始します。")
    
    # 初回実行
    check_prices()
    
    # 定期実行のスケジュール設定
    schedule.every(CHECK_INTERVAL).hours.do(check_prices)
    print(f"{CHECK_INTERVAL}時間ごとに価格チェックを実行するようスケジュールを設定しました。")
    
    # 定期実行ループ
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("プログラムを終了します。")

if __name__ == "__main__":
    main()