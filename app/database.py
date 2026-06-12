"""
数据库初始化 & Session 管理
支持 PostgreSQL（默认）和 SQLite
"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel import SQLModel

from app.config import settings

db_url = settings.database_url

connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

# --- PostgreSQL ---
if db_url.startswith("postgresql"):
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    connect_args = {"connect_timeout": 5}  # 5 秒超时，防止卡死

# --- SQLite ---
elif db_url.startswith("sqlite"):
    # 处理相对路径
    db_path = db_url.replace("sqlite:///", "")
    if not db_path.startswith("/"):
        db_path = os.path.join(os.getcwd(), db_path)
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    db_url = f"sqlite:///{db_path}"
    connect_args = {"check_same_thread": False}

engine = create_engine(db_url, echo=False, connect_args=connect_args, **engine_kwargs)

# SQLite 特殊设置
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
