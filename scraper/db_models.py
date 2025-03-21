from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime
import os

# データベースのパス設定
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'deal_tracker.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# データベースエンジンを作成
engine = create_engine(f'sqlite:///{DB_PATH}', echo=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Item(Base):
    """商品テーブル"""
    __tablename__ = 'items'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False, unique=True)
    site = Column(String(50), nullable=False)  # 'amazon' or 'rakuten'
    category = Column(String(100))
    normal_price = Column(Float, nullable=False)
    current_price = Column(Float)
    image_url = Column(String(1024))
    description = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    
    # リレーションシップ
    price_histories = relationship("PriceHistory", back_populates="item", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="item", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Item(name='{self.name}', current_price={self.current_price})>"

class PriceHistory(Base):
    """価格履歴テーブル"""
    __tablename__ = 'price_histories'
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    price = Column(Float, nullable=False)
    discount_rate = Column(Float)  # 割引率（％）
    timestamp = Column(DateTime, default=datetime.datetime.now)
    
    # リレーションシップ
    item = relationship("Item", back_populates="price_histories")
    
    def __repr__(self):
        return f"<PriceHistory(item_id={self.item_id}, price={self.price}, timestamp='{self.timestamp}')>"

class Notification(Base):
    """通知履歴テーブル"""
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    price = Column(Float, nullable=False)
    discount_rate = Column(Float, nullable=False)
    buy_score = Column(Integer)  # 買い時スコア（0-100）
    message = Column(Text, nullable=False)
    tweeted = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    
    # リレーションシップ
    item = relationship("Item", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(item_id={self.item_id}, price={self.price}, tweeted={self.tweeted})>"

# テーブル作成関数
def create_tables():
    Base.metadata.create_all(engine)

# データベース初期化関数
def init_db():
    create_tables()
    
if __name__ == "__main__":
    init_db()
    print("Database tables created successfully!")