"""
데이터베이스 세션 관리 및 초기화
"""
import os

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

import config

# SQLAlchemy 베이스 클래스
Base = declarative_base()

# 엔진 및 세션 팩토리
engine = create_engine(
    config.SQLALCHEMY_DATABASE_URI,
    echo=False,
    connect_args={"check_same_thread": False},  # SQLite 멀티스레드 허용
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite foreign key constraints are disabled unless each connection opts in."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

session_factory = sessionmaker(bind=engine)
db_session = scoped_session(session_factory)

# Base.query 단축 속성
Base.query = db_session.query_property()


def init_db():
    """데이터베이스 초기화 - 테이블 생성"""
    # instance 디렉토리가 없으면 생성
    instance_dir = os.path.dirname(config.DATABASE_PATH)
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)

    # 모든 모델 임포트 (테이블 등록을 위해)
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_sqlite_upgrades()
    print(f"[DB] 데이터베이스 초기화 완료: {config.DATABASE_PATH}")


def _apply_lightweight_sqlite_upgrades():
    """Add backward-compatible columns for local SQLite databases created pre-migration."""
    inspector = inspect(engine)
    if "transaction" in inspector.get_table_names():
        columns = {col["name"] for col in inspector.get_columns("transaction")}
        with engine.begin() as conn:
            if "balance" not in columns:
                conn.execute(text("ALTER TABLE 'transaction' ADD COLUMN balance INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_transaction_date ON 'transaction' (transaction_date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_transaction_account_date ON 'transaction' (account_id, transaction_date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_transaction_person ON 'transaction' (person_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_transaction_alias ON 'transaction' (person_alias_id)"))

    if "stock" in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_name ON stock (name)"))
            try:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_stock_code_not_null ON stock (code) WHERE code IS NOT NULL"))
            except Exception:
                pass

    if "stock_trade" in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_trade_date ON stock_trade (trade_date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_trade_stock_date ON stock_trade (stock_id, trade_date)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_trade_account_date ON stock_trade (account_id, trade_date)"))


def shutdown_session(exception=None):
    """요청 종료 시 세션 정리"""
    db_session.remove()
