from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class ProposalFieldDefinition(Base):
    """proposal_field_definitions — 제안서 필드의 정적 정보 (필드당 1행).

    docs/제안서_자동작성_API_명세서.md §3.1. data_difficulty/collection_difficulty와
    동일한 "고정 참조 데이터" 패턴 — LLM 추출 대상이 아니라 scripts/seed_proposal_fields.py가
    직접 INSERT한다.
    """

    __tablename__ = "proposal_field_definitions"

    field_key: Mapped[str] = mapped_column(String(80), primary_key=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # TEXT(서술형) / CHECKLIST(체크리스트) / TABLE(연도별 표)
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ProposalTemplateFieldMap(Base):
    """proposal_template_field_map — 유형×필드별 필수/선택 (유형-필드 쌍당 1행).

    §3.2. 1차 초안이던 "psst_requirement/rnd_requirement/ir_requirement" 3-컬럼 설계를
    리뷰 중 폐기하고 행 단위로 바꿨다 — 새 지원사업 유형이 추가돼도 이 테이블에 행만
    추가하면 되고 ALTER TABLE이 필요 없다 (교수님 피드백: 표준 양식 고정 대신 확장 가능하게).

    EXCLUDED는 별도 값으로 저장하지 않는다 — 그 유형에 그 필드의 행이 아예 없는 것으로
    표현한다(조회 시 자연히 빠짐).
    """

    __tablename__ = "proposal_template_field_map"

    template_type: Mapped[str] = mapped_column(String(20), primary_key=True)  # PSST / RND / IR
    field_key: Mapped[str] = mapped_column(
        String(80), ForeignKey("proposal_field_definitions.field_key"), primary_key=True
    )
    requirement: Mapped[str] = mapped_column(String(20), nullable=False)  # REQUIRED / OPTIONAL
