from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class FundingProgram(Base):
    """funding_programs — 지원사업 공고 표준화 테이블.

    K-Startup/중소벤처24 OpenAPI나 Startup Plus 크롤링 결과를 이 테이블에
    저장해두고, 추천 API는 저장된 공고만 읽는다.
    """

    __tablename__ = "funding_programs"

    program_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(80), nullable=True)
    eligibility_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    open_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    support_amount_text: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
