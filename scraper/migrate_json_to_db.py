import json
import os
from datetime import datetime
from db_models import Session, Item, PriceHistory, Notification, init_db

def migrate_json_to_db():
    """JSONデータからSQLiteデータベースへ移行する"""
    # JSONファイルのパス
    json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'price_history.json')
    
    # JSONファイルが存在するか確認
    if not os.path.exists(json_path):
        print(f"JSONファイルが見つかりません: {json_path}")
        return
    
    # JSONデータを読み込む
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"JSONファイルの読み込みエラー: {e}")
        return
    
    # データベースを初期化
    init_db()
    
    # セッション作成
    session = Session()
    
    try:
        # 商品データを移行
        for item_name, item_data in data.get('items', {}).items():
            # サイト種別を判断（URLに基づく）
            site = 'amazon' if 'amazon.co.jp' in item_data.get('url', '') else 'rakuten'
            
            # 商品を作成
            item = Item(
                name=item_name,
                url=item_data.get('url', ''),
                site=site,
                normal_price=item_data.get('normal_price', 0),
                active=True
            )
            session.add(item)
            
            # コミットして商品IDを取得
            session.commit()
            
            # 価格履歴を移行
            for history in item_data.get('price_history', []):
                # タイムスタンプをdatetimeオブジェクトに変換
                try:
                    timestamp = datetime.fromisoformat(history.get('timestamp'))
                except:
                    timestamp = datetime.now()
                
                price = history.get('price', 0)
                
                # 割引率を計算
                normal_price = item_data.get('normal_price', 0)
                discount_rate = 0
                if normal_price > 0:
                    discount_rate = round((normal_price - price) / normal_price * 100, 2)
                
                # 価格履歴を作成
                price_history = PriceHistory(
                    item_id=item.id,
                    price=price,
                    discount_rate=discount_rate,
                    timestamp=timestamp
                )
                session.add(price_history)
            
            # 最新の価格を商品に設定
            if item_data.get('price_history'):
                latest_price = item_data['price_history'][-1].get('price', 0)
                item.current_price = latest_price
        
        # 通知データを移行
        for notification in data.get('notifications', []):
            item_name = notification.get('item_name', '')
            
            # 商品名から商品を検索
            item = session.query(Item).filter_by(name=item_name).first()
            if not item:
                continue
            
            # タイムスタンプをdatetimeオブジェクトに変換
            try:
                timestamp = datetime.fromisoformat(notification.get('timestamp'))
            except:
                timestamp = datetime.now()
            
            # 通知を作成
            notif = Notification(
                item_id=item.id,
                price=notification.get('price', 0),
                discount_rate=notification.get('discount', 0),
                message=notification.get('message', ''),
                tweeted=notification.get('tweeted', False),
                timestamp=timestamp
            )
            session.add(notif)
        
        # 変更をコミット
        session.commit()
        print("データベースへの移行が完了しました。")
        
    except Exception as e:
        session.rollback()
        print(f"エラーが発生しました: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    migrate_json_to_db()