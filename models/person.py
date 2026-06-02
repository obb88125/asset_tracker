"""
인물 모델 (예금자 / 거래 상대방)
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class Person(Base):
    """인물 (예금자/거래상대방) 정보"""

    __tablename__ = "person"

    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(String(100), nullable=False, comment="대표명")
    memo = Column(Text, nullable=True, comment="메모")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="생성일시"
    )

    # 관계
    aliases = relationship(
        "PersonAlias", back_populates="person", cascade="all, delete-orphan"
    )
    transactions = relationship("Transaction", back_populates="person")

    def to_dict(self, include_aliases=True):
        """딕셔너리 변환"""
        result = {
            "id": self.id,
            "display_name": self.display_name,
            "memo": self.memo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_aliases:
            result["aliases"] = [a.to_dict() for a in self.aliases]
        return result


class PersonAlias(Base):
    """인물 별칭 (예금자명 변형)"""

    __tablename__ = "person_alias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    person_id = Column(
        Integer, ForeignKey("person.id", ondelete="CASCADE"), nullable=False
    )
    alias_name = Column(String(100), nullable=False, comment="예금자명 변형")

    __table_args__ = (
        UniqueConstraint("alias_name", name="uq_person_alias_name"),
    )

    # 관계
    person = relationship("Person", back_populates="aliases")
    transactions = relationship("Transaction", back_populates="person_alias")

    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "alias_name": self.alias_name,
        }
