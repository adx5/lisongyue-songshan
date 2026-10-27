import os
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

raw_url = os.getenv("DATABASE_URL")
SQLALCHEMY_DATABASE_URL = raw_url.strip().strip("'\"").replace("\n", "").replace("\r", "") if raw_url else None

if SQLALCHEMY_DATABASE_URL:
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    print(f"DEBUG: 正在连接的数据库: {SQLALCHEMY_DATABASE_URL.split('@')[-1]}")
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
else:
    print("⚠️ 未检测到 DATABASE_URL，回退到本地 SQLite 数据库")
    BASE_DIR = Path(__file__).resolve().parent.parent
    DB_PATH = BASE_DIR / "xinshangquan.db"
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 资源表
class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), index=True, comment="标题")
    category = Column(String(50), comment="分类")
    tag = Column(String(50), comment="标签")
    duration = Column(String(50), comment="时长/规格")
    price = Column(Integer, default=0, comment="价格")
    img = Column(Text, comment="封面图")
    desc = Column(Text, comment="描述")
    keywords = Column(Text, comment="搜索关键词")
    created_at = Column(DateTime, default=datetime.utcnow)

# 线索表
class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(String(50), nullable=True)
    resource_name = Column(String(100))
    client_name = Column(String(50), nullable=True)
    contact_info = Column(String(100), nullable=True)
    address = Column(String(200), nullable=True)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# 会议表
class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), comment="会议标题")
    date_str = Column(String(50), comment="日期")
    location = Column(String(50), comment="地点")
    summary = Column(Text, comment="简介")
    content = Column(Text, comment="正文")
    images = Column(Text, comment="图集")
    media_links = Column(Text, comment="媒体链接")
    created_at = Column(DateTime, default=datetime.utcnow)

# 自动建表
try:
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表初始化完成")
except Exception as e:
    print(f"❌ 数据库初始化失败: {e}")