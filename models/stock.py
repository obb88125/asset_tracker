"""
주식 종목 및 매매 모델
"""
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class Stock(Base):
    """주식 종목 정보"""

    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="종목명")
    code = Column(String(20), nullable=True, comment="종목코드")

    __table_args__ = (
        UniqueConstraint("code", name="uq_stock_code"),
        Index("idx_stock_name", "name"),
    )

    # 관계
    trades = relationship(
        "StockTrade", back_populates="stock", cascade="all, delete-orphan"
    )

    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
        }


class StockTrade(Base):
    """주식 매매 내역"""

    __tablename__ = "stock_trade"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(
        Integer, ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    stock_id = Column(
        Integer, ForeignKey("stock.id", ondelete="CASCADE"), nullable=False
    )
    upload_session_id = Column(
        Integer,
        ForeignKey("upload_session.id", ondelete="SET NULL"),
        nullable=True,
    )
    trade_date = Column(DateTime, nullable=False, comment="매매일시")
    type = Column(String(10), nullable=False, comment="매수(buy) 또는 매도(sell)")
    quantity = Column(Integer, nullable=False, comment="수량")
    price_per_unit = Column(Integer, nullable=False, comment="단가")
    total_amount = Column(Integer, nullable=False, comment="총 금액")
    fee = Column(Integer, default=0, comment="수수료")
    tax = Column(Integer, default=0, comment="세금")
    raw_data = Column(Text, nullable=True, comment="원본 행 JSON")

    __table_args__ = (
        Index("idx_stock_trade_date", "trade_date"),
        Index("idx_stock_trade_stock_date", "stock_id", "trade_date"),
        Index("idx_stock_trade_account_date", "account_id", "trade_date"),
    )

    # 관계
    account = relationship("Account", back_populates="stock_trades")
    stock = relationship("Stock", back_populates="trades")
    upload_session = relationship("UploadSession", back_populates="stock_trades")

    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "stock_id": self.stock_id,
            "upload_session_id": self.upload_session_id,
            "trade_date": (
                self.trade_date.isoformat() if self.trade_date else None
            ),
            "type": self.type,
            "quantity": self.quantity,
            "price_per_unit": self.price_per_unit,
            "total_amount": self.total_amount,
            "fee": self.fee,
            "tax": self.tax,
        }
