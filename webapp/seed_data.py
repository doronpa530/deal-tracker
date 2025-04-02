from app import app, db
from models.product import Product
from models.category import Category
from models.price_history import PriceHistory
from datetime import datetime, timedelta
import random

def seed_data():
    """テスト用データを作成する関数"""
    with app.app_context():
        # 既存のデータを削除
        db.session.query(PriceHistory).delete()
        db.session.query(Product).delete()
        db.session.query(Category).delete()
        db.session.commit()
        
        # カテゴリーの作成
        categories = [
            Category(name='家電', slug='kaden'),
            Category(name='スマートホーム', slug='smart-home'),
            Category(name='キッチン用品', slug='kitchen'),
            Category(name='パソコン・周辺機器', slug='pc'),
            Category(name='生活雑貨', slug='goods'),
            Category(name='ファッション', slug='fashion')
        ]
        
        db.session.add_all(categories)
        db.session.commit()
        
        # 商品の作成（Amazon）
        amazon_products = [
            Product(
                platform='Amazon',
                name='象印 炊飯器 5.5合',
                url='https://www.amazon.co.jp/dp/EXAMPLE1',
                image_url='https://via.placeholder.com/300x200',
                description='象印の高性能炊飯器です。独自の圧力IH技術により、ふっくらとした美味しいご飯を炊き上げます。',
                regular_price=24800,
                sale_price=15980,
                discount_rate=35.6,
                buy_score=92,
                category_id=1,  # 家電
                affiliate_url='https://www.amazon.co.jp/dp/EXAMPLE1?tag=affiliate-code'
            ),
            Product(
                platform='Amazon',
                name='Amazon Echo Dot (第5世代)',
                url='https://www.amazon.co.jp/dp/EXAMPLE2',
                image_url='https://via.placeholder.com/300x200',
                description='コンパクトながらパワフルなスマートスピーカーです。Alexaによる音声操作で、音楽再生、スマートホーム制御、情報検索などが可能です。',
                regular_price=7980,
                sale_price=4780,
                discount_rate=40.1,
                buy_score=89,
                category_id=2,  # スマートホーム
                affiliate_url='https://www.amazon.co.jp/dp/EXAMPLE2?tag=affiliate-code'
            ),
            Product(
                platform='Amazon',
                name='シャープ 加湿空気清浄機',
                url='https://www.amazon.co.jp/dp/EXAMPLE3',
                image_url='https://via.placeholder.com/300x200',
                description='高性能フィルターで、PM2.5や花粉、ウイルスなどを除去します。加湿機能付きで、乾燥する季節も快適に過ごせます。',
                regular_price=32800,
                sale_price=24600,
                discount_rate=25.0,
                buy_score=75,
                category_id=1,  # 家電
                affiliate_url='https://www.amazon.co.jp/dp/EXAMPLE3?tag=affiliate-code'
            )
        ]
        
        # 商品の作成（楽天）
        rakuten_products = [
            Product(
                platform='楽天',
                name='パナソニック 電気ケトル 1.0L',
                url='https://item.rakuten.co.jp/example1',
                image_url='https://via.placeholder.com/300x200',
                description='360度回転するコードレス電気ケトルです。沸騰後の自動電源オフ機能や空だき防止機能など、安全機能も充実しています。',
                regular_price=6980,
                sale_price=4980,
                discount_rate=28.7,
                buy_score=82,
                category_id=3,  # キッチン用品
                affiliate_url='https://item.rakuten.co.jp/example1?scid=affiliate-code'
            ),
            Product(
                platform='楽天',
                name='無印良品 オーク材デスク',
                url='https://item.rakuten.co.jp/example2',
                image_url='https://via.placeholder.com/300x200',
                description='シンプルなデザインのオーク材デスクです。優れた耐久性と美しい木目が特徴で、様々なインテリアに調和します。',
                regular_price=29800,
                sale_price=25330,
                discount_rate=15.0,
                buy_score=65,
                category_id=5,  # 生活雑貨
                affiliate_url='https://item.rakuten.co.jp/example2?scid=affiliate-code'
            ),
            Product(
                platform='楽天',
                name='アディダス ランニングシューズ',
                url='https://item.rakuten.co.jp/example3',
                image_url='https://via.placeholder.com/300x200',
                description='軽量でクッション性に優れたランニングシューズです。長距離走でも快適な履き心地を提供します。',
                regular_price=12800,
                sale_price=8960,
                discount_rate=30.0,
                buy_score=78,
                category_id=6,  # ファッション
                affiliate_url='https://item.rakuten.co.jp/example3?scid=affiliate-code'
            )
        ]
        
        all_products = amazon_products + rakuten_products
        db.session.add_all(all_products)
        db.session.commit()
        
        # 価格履歴の作成
        price_histories = []
        for product in all_products:
            # 過去の価格履歴を作成（過去30日分）
            for days_ago in range(30, 0, -1):
                date = datetime.utcnow() - timedelta(days=days_ago)
                
                # 価格変動をシミュレート
                if days_ago > 25:  # 最初はやや高め
                    price_factor = 1.0 + (random.randint(5, 15) / 100)
                elif days_ago > 15:  # 次に少し下がる
                    price_factor = 1.0 + (random.randint(-5, 5) / 100)
                elif days_ago > 5:  # さらに下がる
                    price_factor = 1.0 - (random.randint(0, 8) / 100)
                else:  # 現在の特価
                    price_factor = product.sale_price / product.regular_price
                
                price = int(product.regular_price * price_factor)
                discount = round((1 - (price / product.regular_price)) * 100, 1)
                
                price_histories.append(
                    PriceHistory(
                        product_id=product.id,
                        price=price,
                        discount_rate=discount,
                        recorded_at=date
                    )
                )
        
        db.session.add_all(price_histories)
        db.session.commit()
        
        print(f"データベースにサンプルデータを追加しました: {len(all_products)} 商品, {len(price_histories)} 価格履歴")

if __name__ == "__main__":
    seed_data()