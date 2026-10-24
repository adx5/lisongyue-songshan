import os
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from datetime import datetime

# 尝试加载 .env 文件
load_dotenv()

# 1. 获取 URL 并做强力清理
raw_url = os.getenv("DATABASE_URL")
SQLALCHEMY_DATABASE_URL = raw_url.strip().strip("'\"").replace("\n", "").replace("\r", "") if raw_url else None

if SQLALCHEMY_DATABASE_URL:
    # 2. 驱动替换
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

    print(f"DEBUG: 准备连接的数据库是: {SQLALCHEMY_DATABASE_URL.split('@')[-1]}")
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
else:
    print("⚠️ 未检测到 DATABASE_URL，回退到本地 SQLite 数据库")
    BASE_DIR = Path(__file__).resolve().parent.parent
    DB_PATH = BASE_DIR / "xinshangquan.db"
    engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 🌟 改造后的嵩山文旅资源表
class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), index=True, comment="标题")
    category = Column(String(50), comment="分类：文化/非遗/礼物等")
    tag = Column(String(50), comment="标签")
    duration = Column(String(50), comment="时长/规格")
    price = Column(Integer, default=0, comment="价格")
    img = Column(Text, comment="封面图链接")
    desc = Column(Text, comment="描述")
    keywords = Column(Text, comment="搜索关键词")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")


# 🌟 保留线索表，适配前台表单
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


# 暂时保留的大客户表（后续如果不需要可删）
class VipClient(Base):
    __tablename__ = "vip_clients"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), comment="公司名称")
    banner_url = Column(Text, comment="轮播图链接")
    slogan = Column(String(200), comment="企业Slogan")
    intro = Column(Text, comment="企业介绍")
    gallery_urls = Column(Text, comment="产品图集")
    cases = Column(Text, comment="合作案例")
    phone = Column(String(50), comment="联系电话")
    wechat = Column(String(50), comment="微信号")
    ext_link = Column(String(200), comment="外链")
    is_active = Column(Boolean, default=True, comment="是否上架")
    sort_order = Column(Integer, default=0, comment="排序")
    view_count = Column(Integer, default=0, comment="访问量")
    theme = Column(String(20), default='warm', comment="主题风格")


# 自动建表
try:
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表初始化完成")
except Exception as e:
    print(f"❌ 数据库初始化失败: {e}")

# 删除了旧的 get_prefix 和 seed_initial_data 播种函数，避免旧数据污染