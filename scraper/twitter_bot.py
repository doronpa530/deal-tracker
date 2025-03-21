"""
Twitter通知ボット
"""
import tweepy
from datetime import datetime
import time
from db_models import Session, Notification

# config.pyから設定を読み込み
from config import (
    TWITTER_API_KEY, 
    TWITTER_API_SECRET, 
    TWITTER_ACCESS_TOKEN, 
    TWITTER_ACCESS_SECRET
)

def init_twitter_api():
    """Twitter API の初期化"""
    auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
    return tweepy.API(auth)

def tweet_notification(message):
    """通知をツイート"""
    try:
        api = init_twitter_api()
        api.update_status(message)
        print(f"ツイート送信成功: {message}")
        return True
    except Exception as e:
        print(f"ツイート送信エラー: {e}")
        return False

def process_pending_notifications():
    """未ツイートの通知を処理"""
    session = Session()
    try:
        # 未ツイートの通知を取得
        pending_notifications = session.query(Notification)\
            .filter_by(tweeted=False)\
            .order_by(Notification.timestamp)\
            .all()
        
        print(f"未ツイート通知数: {len(pending_notifications)}")
        
        for notification in pending_notifications:
            print(f"通知処理中: ID={notification.id}")
            
            # 通知メッセージをツイート
            if tweet_notification(notification.message):
                # ツイート成功したらフラグを更新
                notification.tweeted = True
                session.commit()
                print(f"通知ID {notification.id} をツイート済みとしてマーク")
            else:
                # エラー時はロールバック
                session.rollback()
                print(f"通知ID {notification.id} のツイートに失敗")
                
            # レートリミット対策のため少し待機
            time.sleep(2)
            
    except Exception as e:
        session.rollback()
        print(f"通知処理中にエラーが発生: {e}")
    finally:
        session.close()

def create_test_notification():
    """テスト通知を作成（デバッグ用）"""
    from utils import format_notification_message
    from db_models import Item
    
    session = Session()
    try:
        # 最初の商品を取得
        item = session.query(Item).first()
        if not item:
            print("商品が見つかりません")
            return
        
        # テスト割引を設定（通常価格の30%オフ）
        test_price = int(item.normal_price * 0.7)
        test_discount = 30
        test_buy_score = 85
        
        # テスト通知メッセージを生成
        message = format_notification_message(item, test_price, test_discount, test_buy_score)
        
        # 通知を作成
        notification = Notification(
            item_id=item.id,
            price=test_price,
            discount_rate=test_discount,
            buy_score=test_buy_score,
            message=message,
            tweeted=False,
            timestamp=datetime.now()
        )
        
        session.add(notification)
        session.commit()
        print(f"テスト通知を作成しました: {message}")
        
    except Exception as e:
        session.rollback()
        print(f"テスト通知作成中にエラーが発生: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print(f"Twitter Bot 実行開始: {datetime.now()}")
    
    # コマンドライン引数で動作を切り替える（テスト用）
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("テスト通知を作成します...")
        create_test_notification()
    
    # 通知処理
    process_pending_notifications()
    
    print(f"Twitter Bot 実行完了: {datetime.now()}")