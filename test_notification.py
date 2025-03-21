"""
テスト通知を作成するスクリプト
"""
from datetime import datetime
from scraper.db_models import Session, Item, Notification
from scraper.utils import format_notification_message

def create_test_notification():
    """テスト通知を作成"""
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
    create_test_notification()