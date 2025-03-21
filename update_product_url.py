# update_product_url.py として保存
from scraper.db_models import Session, Item

# 新しいURLを指定
new_url = "https://www.amazon.co.jp/dp/B019GNUT0C/"

# データベースセッションを作成
session = Session()

try:
    # Anker PowerCoreを検索
    item = session.query(Item).filter_by(name="Anker PowerCore").first()
    if item:
        # 古いURLを記録
        old_url = item.url
        
        # URLを更新
        item.url = new_url
        session.commit()
        print(f"URLを更新しました: {item.name}")
        print(f"古いURL: {old_url}")
        print(f"新しいURL: {new_url}")
    else:
        print("商品が見つかりませんでした")
finally:
    session.close()