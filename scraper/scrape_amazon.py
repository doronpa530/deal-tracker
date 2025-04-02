# scraper/scrape_amazon.py
import requests
from bs4 import BeautifulSoup
import time
import re
import os
import json
import random
from datetime import datetime
from pathlib import Path
from db_models import Session, Item, PriceHistory, Notification
import logging

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "amazon_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('amazon_scraper')

# スクレイパー設定読み込み
SCRAPER_CONFIG_PATH = Path(__file__).parent / 'scraper_config.json'

def load_config():
    """設定ファイルを読み込む"""
    if SCRAPER_CONFIG_PATH.exists():
        with open(SCRAPER_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # デフォルト設定
        default_config = {
            "amazon": {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                "request_delay": 3,
                "categories": {
                    "electronics": {
                        "name": "家電&カメラ",
                        "url": "https://www.amazon.co.jp/gp/bestsellers/electronics/",
                        "active": True
                    },
                    "computers": {
                        "name": "パソコン・周辺機器",
                        "url": "https://www.amazon.co.jp/gp/bestsellers/computers/",
                        "active": True
                    },
                    "kitchen": {
                        "name": "ホーム&キッチン",
                        "url": "https://www.amazon.co.jp/gp/bestsellers/kitchen/",
                        "active": True
                    },
                    "toys": {
                        "name": "おもちゃ",
                        "url": "https://www.amazon.co.jp/gp/bestsellers/toys/",
                        "active": True
                    }
                },
                "time_sale_url": "https://www.amazon.co.jp/deals",
                "active": True
            }
        }
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(SCRAPER_CONFIG_PATH), exist_ok=True)
        with open(SCRAPER_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        return default_config

def get_headers():
    """リクエストヘッダーを生成"""
    config = load_config()
    user_agent = config["amazon"]["user_agent"]
    return {
        "User-Agent": user_agent,
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }

def extract_asin(url):
    """URLからASINを抽出"""
    asin_match = re.search(r'/dp/([A-Z0-9]{10})/?', url)
    if asin_match:
        return asin_match.group(1)
    return None

def get_product_details(url, retry=3):
    """商品ページから詳細情報を取得"""
    headers = get_headers()
    config = load_config()
    delay = config["amazon"]["request_delay"]
    
    # リクエスト前に少し待機
    time.sleep(delay * (1 + random.random()))
    
    for attempt in range(retry):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # 商品名
                title_element = soup.select_one("#productTitle")
                title = title_element.get_text(strip=True) if title_element else "不明な商品"
                
                # 現在価格
                price = extract_price(soup)
                
                # 商品画像
                img_element = soup.select_one("#landingImage") or soup.select_one("#imgBlkFront")
                img_url = img_element.get('src') if img_element else None
                
                # レビュー数と評価
                rating = None
                review_count = None
                review_element = soup.select_one("#acrCustomerReviewText")
                if review_element:
                    review_text = review_element.get_text(strip=True)
                    review_match = re.search(r'([\d,]+)', review_text)
                    if review_match:
                        review_count = int(review_match.group(1).replace(',', ''))
                
                rating_element = soup.select_one(".a-icon-star")
                if rating_element:
                    rating_text = rating_element.get_text(strip=True)
                    rating_match = re.search(r'([\d.]+)', rating_text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                
                # カテゴリ
                category = None
                breadcrumb = soup.select_one("#wayfinding-breadcrumbs_feature_div")
                if breadcrumb:
                    categories = breadcrumb.select(".a-link-normal")
                    if categories:
                        category = categories[-1].get_text(strip=True)
                
                # デバッグ用にHTMLを保存
                debug_dir = Path(__file__).parent.parent / 'debug'
                os.makedirs(debug_dir, exist_ok=True)
                with open(debug_dir / f"amazon_detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                
                return {
                    "title": title,
                    "price": price,
                    "img_url": img_url,
                    "rating": rating,
                    "review_count": review_count,
                    "category": category,
                    "url": url,
                    "asin": extract_asin(url)
                }
            
            elif response.status_code == 429 or response.status_code == 503:
                # レート制限やサービス一時停止の場合は待機時間を長くして再試行
                wait_time = delay * (2 ** attempt) * (1 + random.random())
                logger.warning(f"レート制限または一時停止エラー（{response.status_code}）。{wait_time:.1f}秒待機して再試行します。")
                time.sleep(wait_time)
                continue
            
            else:
                logger.error(f"HTTPエラー: {response.status_code}, URL: {url}")
                return None
                
        except Exception as e:
            logger.error(f"商品詳細取得中にエラー発生: {e}")
            if attempt < retry - 1:
                time.sleep(delay * (2 ** attempt))
                continue
            else:
                return None
    
    return None

def extract_price(soup):
    """BeautifulSoupオブジェクトから価格を抽出"""
    # 複数の価格要素セレクタを試す
    selectors = [
        ".a-price .a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        ".apexPriceToPay .a-offscreen",
        "#corePrice_feature_div .a-price .a-offscreen"
    ]
    
    for selector in selectors:
        price_element = soup.select_one(selector)
        if price_element:
            price_text = price_element.get_text(strip=True)
            price_clean = re.sub(r'[^\d.]', '', price_text)
            try:
                return int(float(price_clean))
            except ValueError:
                continue
    
    return None

def scrape_bestsellers(category_key=None):
    """Amazonベストセラーのスクレイピング"""
    config = load_config()
    categories = config["amazon"]["categories"]
    
    # カテゴリキーが指定されていない場合はすべてのアクティブなカテゴリを処理
    if category_key is None:
        active_categories = {k: v for k, v in categories.items() if v.get("active", True)}
    else:
        # 指定されたカテゴリが存在しアクティブな場合のみ処理
        if category_key in categories and categories[category_key].get("active", True):
            active_categories = {category_key: categories[category_key]}
        else:
            logger.error(f"カテゴリが見つからないか非アクティブです: {category_key}")
            return
    
    logger.info(f"処理するカテゴリ: {', '.join(active_categories.keys())}")
    
    # 各カテゴリのベストセラーをスクレイピング
    for cat_key, cat_info in active_categories.items():
        logger.info(f"カテゴリ '{cat_info['name']}' のスクレイピングを開始")
        url = cat_info["url"]
        
        try:
            # カテゴリページにアクセス
            headers = get_headers()
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"HTTPエラー: {response.status_code}, URL: {url}")
                continue
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # ランキング商品を抽出
            product_elements = soup.select("#zg-ordered-list .zg-item-immersion")
            
            if not product_elements:
                logger.warning(f"商品要素が見つかりませんでした: {url}")
                # デバッグ用にHTMLを保存
                debug_dir = Path(__file__).parent.parent / 'debug'
                os.makedirs(debug_dir, exist_ok=True)
                with open(debug_dir / f"amazon_bestseller_{cat_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                continue
            
            logger.info(f"{len(product_elements)}件の商品を検出")
            
            # 商品情報を処理
            for i, product in enumerate(product_elements[:20]):  # 上位20件を処理
                # 商品リンク
                link_element = product.select_one(".a-link-normal[href*='/dp/']")
                if not link_element:
                    continue
                
                product_url = "https://www.amazon.co.jp" + link_element["href"] if link_element["href"].startswith("/") else link_element["href"]
                asin = extract_asin(product_url)
                
                if not asin:
                    logger.warning(f"ASINを抽出できませんでした: {product_url}")
                    continue
                
                # ランキング
                rank = i + 1
                
                logger.info(f"商品 {rank}: ASIN={asin}, URL={product_url}")
                
                # データベースに既存の商品があるか確認
                session = Session()
                try:
                    existing_item = session.query(Item).filter_by(product_id=asin, site="amazon").first()
                    
                    if existing_item:
                        logger.info(f"既存商品を更新: {asin}")
                        
                        # 詳細情報を取得
                        details = get_product_details(product_url)
                        if not details:
                            logger.warning(f"商品詳細を取得できませんでした: {asin}")
                            continue
                        
                        # 価格変動を確認
                        old_price = existing_item.current_price
                        new_price = details["price"]
                        
                        if old_price != new_price and new_price is not None:
                            # 価格履歴を追加
                            discount_rate = 0
                            if existing_item.normal_price > 0 and new_price < existing_item.normal_price:
                                discount_rate = round((existing_item.normal_price - new_price) / existing_item.normal_price * 100, 2)
                            
                            price_history = PriceHistory(
                                item_id=existing_item.id,
                                price=new_price,
                                discount_rate=discount_rate,
                                timestamp=datetime.now()
                            )
                            session.add(price_history)
                            
                            # 大幅値下げの場合は通知
                            if discount_rate >= 20:  # 20%以上の値下げ
                                from utils import format_notification_message
                                buy_score = calculate_buy_score(existing_item.id, new_price, existing_item.normal_price)
                                
                                message = format_notification_message(existing_item, new_price, discount_rate, buy_score)
                                
                                notification = Notification(
                                    item_id=existing_item.id,
                                    price=new_price,
                                    discount_rate=discount_rate,
                                    buy_score=buy_score,
                                    message=message,
                                    tweeted=False,
                                    timestamp=datetime.now()
                                )
                                session.add(notification)
                                logger.info(f"通知を作成: {existing_item.name}, 割引率={discount_rate}%")
                        
                        # 既存商品の情報を更新
                        existing_item.name = details["title"]
                        existing_item.current_price = new_price
                        if details["img_url"]:
                            existing_item.image_url = details["img_url"]
                        existing_item.rank = rank
                        existing_item.updated_at = datetime.now()
                        
                    else:
                        logger.info(f"新規商品を追加: {asin}")
                        
                        # 詳細情報を取得
                        details = get_product_details(product_url)
                        if not details or not details["price"]:
                            logger.warning(f"商品詳細または価格が取得できませんでした: {asin}")
                            continue
                        
                        # 新しい商品を追加
                        new_item = Item(
                            product_id=asin,
                            name=details["title"],
                            url=product_url,
                            site="amazon",
                            category=cat_key,
                            normal_price=details["price"],
                            current_price=details["price"],
                            image_url=details["img_url"],
                            rank=rank,
                            data_source="ranking",
                            active=True,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        session.add(new_item)
                        session.flush()  # IDを生成するためにフラッシュ
                        
                        # 初期価格履歴を追加
                        price_history = PriceHistory(
                            item_id=new_item.id,
                            price=details["price"],
                            discount_rate=0,
                            timestamp=datetime.now()
                        )
                        session.add(price_history)
                    
                    # 変更をコミット
                    session.commit()
                    
                except Exception as e:
                    session.rollback()
                    logger.error(f"データベース操作中にエラー発生: {e}")
                finally:
                    session.close()
                
                # リクエスト間隔を空ける
                time.sleep(config["amazon"]["request_delay"] * (1 + random.random() * 0.5))
            
            logger.info(f"カテゴリ '{cat_info['name']}' のスクレイピングが完了")
            
        except Exception as e:
            logger.error(f"カテゴリ '{cat_info['name']}' のスクレイピング中にエラー発生: {e}")
            import traceback
            logger.error(traceback.format_exc())

def scrape_timesales():
    """Amazonタイムセールのスクレイピング"""
    config = load_config()
    url = config["amazon"]["time_sale_url"]
    
    logger.info("タイムセールのスクレイピングを開始")
    
    try:
        # タイムセールページにアクセス
        headers = get_headers()
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"HTTPエラー: {response.status_code}, URL: {url}")
            return
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # デバッグ用にHTMLを保存
        debug_dir = Path(__file__).parent.parent / 'debug'
        os.makedirs(debug_dir, exist_ok=True)
        with open(debug_dir / f"amazon_timesale_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        # タイムセール商品を抽出
        product_elements = soup.select(".a-carousel-card")
        
        if not product_elements:
            logger.warning(f"タイムセール商品が見つかりませんでした: {url}")
            return
        
        logger.info(f"{len(product_elements)}件のタイムセール商品を検出")
        
        # 商品情報を処理
        for product in product_elements:
            # 商品リンク
            link_element = product.select_one("a[href*='/dp/']")
            if not link_element:
                continue
            
            product_url = "https://www.amazon.co.jp" + link_element["href"] if link_element["href"].startswith("/") else link_element["href"]
            asin = extract_asin(product_url)
            
            if not asin:
                logger.warning(f"ASINを抽出できませんでした: {product_url}")
                continue
            
            logger.info(f"タイムセール商品: ASIN={asin}, URL={product_url}")
            
            # データベースに既存の商品があるか確認
            session = Session()
            try:
                existing_item = session.query(Item).filter_by(product_id=asin, site="amazon").first()
                
                # 詳細情報を取得
                details = get_product_details(product_url)
                if not details or not details["price"]:
                    logger.warning(f"商品詳細または価格が取得できませんでした: {asin}")
                    continue
                
                if existing_item:
                    logger.info(f"既存商品を更新 (タイムセール): {asin}")
                    
                    # 価格変動を確認
                    old_price = existing_item.current_price
                    new_price = details["price"]
                    
                    if old_price != new_price and new_price is not None:
                        # 価格履歴を追加
                        discount_rate = 0
                        if existing_item.normal_price > 0 and new_price < existing_item.normal_price:
                            discount_rate = round((existing_item.normal_price - new_price) / existing_item.normal_price * 100, 2)
                        
                        price_history = PriceHistory(
                            item_id=existing_item.id,
                            price=new_price,
                            discount_rate=discount_rate,
                            timestamp=datetime.now()
                        )
                        session.add(price_history)
                        
                        # 大幅値下げの場合は通知
                        if discount_rate >= 20:  # 20%以上の値下げ
                            from utils import format_notification_message
                            buy_score = calculate_buy_score(existing_item.id, new_price, existing_item.normal_price)
                            
                            message = format_notification_message(existing_item, new_price, discount_rate, buy_score)
                            
                            notification = Notification(
                                item_id=existing_item.id,
                                price=new_price,
                                discount_rate=discount_rate,
                                buy_score=buy_score,
                                message=message,
                                tweeted=False,
                                timestamp=datetime.now()
                            )
                            session.add(notification)
                            logger.info(f"通知を作成 (タイムセール): {existing_item.name}, 割引率={discount_rate}%")
                    
                    # 既存商品の情報を更新
                    existing_item.name = details["title"]
                    existing_item.current_price = new_price
                    if details["img_url"]:
                        existing_item.image_url = details["img_url"]
                    existing_item.data_source = "timesale"
                    existing_item.updated_at = datetime.now()
                    
                else:
                    logger.info(f"新規商品を追加 (タイムセール): {asin}")
                    
                    # 新しい商品を追加
                    new_item = Item(
                        product_id=asin,
                        name=details["title"],
                        url=product_url,
                        site="amazon",
                        category=details["category"],
                        normal_price=details["price"],  # セール価格を通常価格としても設定（暫定）
                        current_price=details["price"],
                        image_url=details["img_url"],
                        data_source="timesale",
                        active=True,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    session.add(new_item)
                    session.flush()  # IDを生成するためにフラッシュ
                    
                    # 初期価格履歴を追加
                    price_history = PriceHistory(
                        item_id=new_item.id,
                        price=details["price"],
                        discount_rate=0,
                        timestamp=datetime.now()
                    )
                    session.add(price_history)
                
                # 変更をコミット
                session.commit()
                
            except Exception as e:
                session.rollback()
                logger.error(f"データベース操作中にエラー発生: {e}")
                import traceback
                logger.error(traceback.format_exc())
            finally:
                session.close()
            
            # リクエスト間隔を空ける
            time.sleep(config["amazon"]["request_delay"] * (1 + random.random() * 0.5))
        
        logger.info("タイムセールのスクレイピングが完了")
        
    except Exception as e:
        logger.error(f"タイムセールのスクレイピング中にエラー発生: {e}")
        import traceback
        logger.error(traceback.format_exc())

def calculate_buy_score(item_id, current_price, normal_price):
    """買い時スコアを計算（0-100）"""
    # 基本スコア：現在の割引率に基づく（最大60点）
    discount = 0
    if normal_price > 0 and current_price < normal_price:
        discount = round((normal_price - current_price) / normal_price * 100, 2)
    
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
        logger.error(f"履歴スコア計算エラー: {e}")
        history_score = 20  # エラー時は中間点
    finally:
        session.close()
    
    # 総合スコア（四捨五入して整数に）
    total_score = round(base_score + history_score)
    
    # 0-100の範囲に収める
    return max(0, min(100, total_score))

def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Amazonスクレイピング')
    parser.add_argument('--category', help='スクレイピングするカテゴリ')
    parser.add_argument('--timesale', action='store_true', help='タイムセールをスクレイピング')
    parser.add_argument('--all', action='store_true', help='すべてのカテゴリとタイムセールをスクレイピング')
    
    args = parser.parse_args()
    
    if args.all:
        logger.info("すべてのカテゴリとタイムセールのスクレイピングを開始")
        scrape_bestsellers()
        scrape_timesales()
    elif args.timesale:
        logger.info("タイムセールのスクレイピングを開始")
        scrape_timesales()
    elif args.category:
        logger.info(f"カテゴリ '{args.category}' のスクレイピングを開始")
        scrape_bestsellers(args.category)
    else:
        logger.info("デフォルトでベストセラーのスクレイピングを開始")
        scrape_bestsellers()
    
    logger.info("スクレイピングが完了しました")

if __name__ == "__main__":
    main()