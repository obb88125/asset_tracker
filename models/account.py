"""
계좌 모델
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class Account(Base):
    """금융 계좌 정보"""

    __tablename__ = "account"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="계좌 별칭")
    institution = Column(String(100), nullable=False, comment="금융기관명")
    account_number = Column(String(50), nullable=True, comment="계좌번호")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="생성일시"
    )

    # 관계
    transactions = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
    stock_trades = relationship(
        "StockTrade", back_populates="account", cascade="all, delete-orphan"
    )
    upload_sessions = relationship(
        "UploadSession", back_populates="account", cascade="all, delete-orphan"
    )

    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "institution": self.institution,
            "account_number": self.account_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
