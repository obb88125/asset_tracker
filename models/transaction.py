"""
거래(입출금) 모델
"""
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class Transaction(Base):
    """입출금 거래 내역"""

    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(
        Integer, ForeignKey("account.id", ondelete="CASCADE"), nullable=False
    )
    person_alias_id = Column(
        Integer,
        ForeignKey("person_alias.id", ondelete="SET NULL"),
        nullable=True,
    )
    person_id = Column(
        Integer, ForeignKey("person.id", ondelete="SET NULL"), nullable=True
    )
    upload_session_id = Column(
        Integer,
        ForeignKey("upload_session.id", ondelete="SET NULL"),
        nullable=False,
    )
    transaction_date = Column(DateTime, nullable=False, comment="거래일시")
    type = Column(String(20), nullable=False, comment="입금(deposit) 또는 출금(withdrawal)")
    amount = Column(Integer, nullable=False, comment="금액 (원 단위 정수)")
    counterparty_raw = Column(String(200), nullable=False, comment="원본 예금자명")
    description = Column(Text, nullable=True, comment="적요")
    raw_data = Column(Text, nullable=True, comment="원본 행 JSON")

    # 관계
    account = relationship("Account", back_populates="transactions")
    person_alias = relationship("PersonAlias", back_populates="transactions")
    person = relationship("Person", back_populates="transactions")
    upload_session = relationship("UploadSession", back_populates="transactions")

    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "person_alias_id": self.person_alias_id,
            "person_id": self.person_id,
            "upload_session_id": self.upload_session_id,
            "transaction_date": (
                self.transaction_date.isoformat() if self.transaction_date else None
            ),
            "type": self.type,
            "amount": self.amount,
            "counterparty_raw": self.counterparty_raw,
            "description": self.description,
        }
