"""
데이터베이스 세션 관리 및 초기화
"""
import os

from sqlalchemy import create_engine
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
    print(f"[DB] 데이터베이스 초기화 완료: {config.DATABASE_PATH}")


def shutdown_session(exception=None):
    """요청 종료 시 세션 정리"""
    db_session.remove()
