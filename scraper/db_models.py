from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from datetime import datetime
import os

# データベースのパス設定
if 'PYTHONANYWHERE_DOMAIN' in os.environ:
    # PythonAnywhere環境
    db_path = os.path.expanduser('~/deal_tracker.db')
else:
    # ローカル環境
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'deal_tracker.db')

# データベース接続設定
engine = create_engine(f'sqlite:///{db_path}', echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# モデル定義
class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    site = Column(String(20), nullable=False)  # 'amazon'/'rakuten'/'both'
    url_path = Column(String(255))
    active = Column(Integer, default=1)
    
    # 自己参照リレーションシップ
    subcategories = relationship(
        'Category', 
        backref=backref('parent', remote_side=[id]),
        lazy='dynamic'
    )
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Item(Base):
    __tablename__ = 'items'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(String(50), nullable=False)
    site = Column(String(20), nullable=False)  # 'amazon'/'rakuten'
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False, unique=True)
    category_id = Column(Integer, ForeignKey('categories.id'))
    normal_price = Column(Float, nullable=False)
    current_price = Column(Float)
    image_url = Column(String(1024))
    description = Column(Text)
    rank = Column(Integer)
    rating = Column(Float)
    review_count = Column(Integer)
    data_source = Column(String(50))
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # リレーションシップ
    category = relationship('Category', backref='items')
    price_histories = relationship('PriceHistory', back_populates='item', cascade='all, delete-orphan')
    notifications = relationship('Notification', back_populates='item', cascade='all, delete-orphan')
    
    def calculate_discount_rate(self):
        if self.normal_price > 0 and self.current_price:
            return round((1 - (self.current_price / self.normal_price)) * 100, 1)
        return 0
    
    def __repr__(self):
        return f'<Item {self.name}>'

class PriceHistory(Base):
    __tablename__ = 'price_histories'
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    price = Column(Float, nullable=False)
    discount_rate = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    item = relationship('Item', back_populates='price_histories')
    
    def __repr__(self):
        return f'<PriceHistory {self.item_id} - {self.price}>'

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    price = Column(Float, nullable=False)
    discount_rate = Column(Float, nullable=False)
    buy_score = Column(Integer)
    message = Column(Text, nullable=False)
    tweeted = Column(Integer, default=0)
    web_displayed = Column(Integer, default=0)
    notification_type = Column(String(20))
    timestamp = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    item = relationship('Item', back_populates='notifications')
    
    def __repr__(self):
        return f'<Notification {self.item_id} - {self.price}>'

# 統計情報テーブル
class ItemStatistics(Base):
    __tablename__ = 'item_statistics'
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'), unique=True)
    avg_price = Column(Float)
    min_price = Column(Float)
    max_price = Column(Float)
    price_volatility = Column(Float)
    last_discount_date = Column(DateTime)
    discount_frequency = Column(Integer)
    updated_at = Column(DateTime)
    
    # リレーションシップ
    item = relationship('Item', backref='statistics')
    
    def __repr__(self):
        return f'<ItemStatistics {self.item_id}>'

# スクレイピングログテーブル
class ScrapingLog(Base):
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True)
    site = Column(String(20), nullable=False)
    category_id = Column(Integer)
    status = Column(String(20), nullable=False)
    items_processed = Column(Integer)
    items_added = Column(Integer)
    items_updated = Column(Integer)
    price_changes_detected = Column(Integer)
    error_message = Column(Text)
    execution_time = Column(Float)
    timestamp = Column(DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<ScrapingLog {self.site} - {self.timestamp}>'

# データベース初期化関数
def init_db():
    Base.metadata.create_all(engine)