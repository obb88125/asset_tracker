"""
업로드 세션 모델
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class UploadSession(Base):
    """파일 업로드 세션 정보"""

    __tablename__ = "upload_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(
        Integer, ForeignKey("account.id", ondelete="SET NULL"), nullable=True
    )
    filename = Column(String(255), nullable=False, comment="업로드 파일명")
    file_type = Column(String(10), nullable=False, comment="파일 유형 (xlsx, csv 등)")
    column_mapping = Column(Text, nullable=True, comment="컬럼 매핑 정보 (JSON)")
    total_rows = Column(Integer, default=0, comment="전체 행 수")
    imported_rows = Column(Integer, default=0, comment="임포트된 행 수")
    uploaded_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="업로드 일시",
    )

    # 관계
    account = relationship("Account", back_populates="upload_sessions")
    transactions = relationship("Transaction", back_populates="upload_session")
    stock_trades = relationship("StockTrade", back_populates="upload_session")

    def to_dict(self):
        """딕셔너리 변환"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "column_mapping": self.column_mapping,
            "total_rows": self.total_rows,
            "imported_rows": self.imported_rows,
            "uploaded_at": (
                self.uploaded_at.isoformat() if self.uploaded_at else None
            ),
        }
