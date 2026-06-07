"""
数据库初始化 & Session 管理
"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel import SQLModel

from app.config import settings

# 确保数据目录存在
os.makedirs(os.path.dirname(settings.database_url.replace("sqlite:///", "")), exist_ok=True)

# 处理 SQLite 的路径问题
db_url = settings.database_url
if db_url.startswith("sqlite:///"):
    db_path = db_url.replace("sqlite:///", "")
    if not db_path.startswith("/"):
        db_path = os.path.join(os.getcwd(), db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db_url = f"sqlite:///{db_path}"

connect_args = {"check_same_thread": False} if "sqlite" in db_url else {}

engine = create_engine(
    db_url,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# 为 SQLite 启用 WAL 模式和外键
if "sqlite" in db_url:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,
)


def init_db():
    """创建所有表"""
    from app.models import task, domain, asset, vulnerability, rule  # noqa: ensure models loaded
    SQLModel.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Session:
    """获取数据库 session 的 context manager"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """FastAPI 依赖注入用 generator"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
