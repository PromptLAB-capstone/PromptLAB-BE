"""제안서 자동 작성 기능(이슈 #102)의 필드 매트릭스를 시딩한다.

값의 원본은 docs/제안서_자동작성_API_명세서.md §2(유형별 필드 매트릭스)다. 그 문서의
표를 그대로 옮기되, "정의(FIELD_DEFINITIONS)"와 "유형별 필수/선택(TEMPLATE_FIELD_ROWS)"을
한 소스(_MATRIX)에서 함께 파생시켜 — 문서 표를 고칠 때 두 리스트가 따로 놀며 어긋나는
사고를 구조적으로 막는다.

재실행해도 안전하다(있으면 갱신, 없으면 삽입).

    python scripts/seed_proposal_fields.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.models import ProposalFieldDefinition, ProposalTemplateFieldMap
from app.db.session import AsyncSessionLocal

TEMPLATE_TYPES = ("PSST", "RND", "IR")

# (field_key, category, label, field_type, PSST, RND, IR)
# PSST/RND/IR 값: "REQUIRED" / "OPTIONAL" / None(제외 -- 매핑 행 자체를 만들지 않음)
_R = "REQUIRED"
_O = "OPTIONAL"
_MATRIX: list[tuple[str, str, str, str, str | None, str | None, str | None]] = [
    # 2.0 일반현황·개요
    ("company_overview", "일반현황", "기업개요·대표자", "TEXT", _R, _R, _R),
    ("idea_overview", "일반현황", "창업아이템 개요", "TEXT", _R, _R, _R),
    ("location_timing", "일반현황", "창업예정지·시기", "TEXT", _R, _O, None),
    ("project_period", "일반현황", "사업 수행기간(총수행기간·협약기간)", "TEXT", _R, _R, _R),
    # 2.1 문제인식
    ("background_motivation", "문제인식", "개발 배경·동기", "TEXT", _R, _R, _R),
    ("target_market_analysis", "문제인식", "목표시장 분석", "TEXT", _R, _R, _R),
    # 2.2 실현가능성
    ("dev_status", "실현가능성", "개발/사업화 현황", "TEXT", _R, _R, _R),
    ("feasibility_diff", "실현가능성", "실현방안·차별점", "TEXT", _R, _R, _R),
    ("ip_plan", "실현가능성", "지식재산권 확보 계획", "TEXT", None, _O, _O),
    # 2.3 성장전략
    ("funding_plan", "성장전략", "자금조달 계획", "TEXT", _R, _R, _R),
    ("revenue_model", "성장전략", "수익모델·시장진입", "TEXT", _R, _R, _R),
    ("schedule", "성장전략", "사업 추진 일정", "TEXT", _R, _R, _R),
    ("growth_targets", "성장전략", "정량적 성장목표(3개년 매출·고용 수치)", "TABLE", _R, _R, _R),
    ("exit_strategy", "성장전략", "출구(EXIT) 전략", "TEXT", None, None, _O),
    ("overseas_expansion", "성장전략", "해외시장 진출전략(타겟국가·GTM·진출실적)", "TEXT", _O, None, _O),
    # 2.4 팀 구성
    ("founder_capability", "팀구성", "대표자 역량", "TEXT", _R, _R, _R),
    ("team_hiring_plan", "팀구성", "팀 구성·고용계획", "TEXT", _R, _R, _R),
    ("new_hire_plan", "팀구성", "신규 인력 채용계획(고용창출 목표, 정량)", "TEXT", None, _R, _O),
    ("partnership", "팀구성", "파트너십·외부협력", "TEXT", None, _O, _O),
    # 2.5 PREP 특화 항목
    ("regulatory_compliance", "PREP특화", "규제 준수 및 리스크 대응", "TEXT", _R, _R, _O),
    ("data_strategy", "PREP특화", "데이터 확보 전략", "TEXT", _R, _R, _O),
    ("general_risk_mgmt", "PREP특화", "일반 리스크 관리 계획(시장·운영 리스크)", "TEXT", _O, _O, _O),
    ("program_utilization", "PREP특화", "지원 프로그램 활용계획(참가목적 등)", "TEXT", _O, _O, _O),
    # 2.6 R&D 특화 항목
    ("rd_plan_budget", "RND특화", "연구개발목표·연구비산정·참여연구원", "TEXT", None, _R, None),
    ("annual_budget_exec", "RND특화", "연차별 사업비 집행계획(정부출연금/자기부담금 현금·현물 구분)", "TABLE", None, _R, None),
    ("rd_track_record", "RND특화", "정부지원 수혜실적 및 기존 R&D 이력", "TEXT", None, _R, None),
    ("trl_level", "RND특화", "기술성숙도(TRL, 1~9단계) 현재 수준 및 목표 수준", "TEXT", None, _R, _O),
    # 2.7 투자유치용(IR) 추가 항목
    ("esg", "IR추가", "사회적 가치·ESG", "TEXT", None, None, _O),
    ("bonus_criteria", "IR추가", "우대 가점 사항", "TEXT", None, _O, _O),
    ("financial_projection", "IR추가", "재무 추정(3~5개년, BEP)", "TABLE", None, None, _O),
    ("tam_sam_som", "IR추가", "TAM/SAM/SOM 시장규모", "TEXT", None, None, _O),
    ("cap_table", "IR추가", "지분구조(캡테이블)", "TABLE", None, None, _O),
    # 2.8 첨부서류
    ("attachment_checklist", "첨부서류", "첨부서류 체크리스트(사업자등록증·재무제표·납세증명서 등)", "CHECKLIST", _R, _R, _R),
]


def _field_definitions() -> list[dict]:
    return [
        {
            "field_key": row[0],
            "category": row[1],
            "label": row[2],
            "field_type": row[3],
            "display_order": (index + 1) * 10,
        }
        for index, row in enumerate(_MATRIX)
    ]


def _template_field_rows() -> list[dict]:
    rows: list[dict] = []
    for field_key, *_rest, psst, rnd, ir in _MATRIX:
        for template_type, requirement in zip(TEMPLATE_TYPES, (psst, rnd, ir)):
            if requirement is not None:
                rows.append(
                    {"template_type": template_type, "field_key": field_key, "requirement": requirement}
                )
    return rows


FIELD_DEFINITION_ROWS = _field_definitions()
TEMPLATE_FIELD_ROWS = _template_field_rows()


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        for row in FIELD_DEFINITION_ROWS:
            existing = await session.get(ProposalFieldDefinition, row["field_key"])
            if existing is None:
                session.add(ProposalFieldDefinition(**row, description=None))
            else:
                existing.category = row["category"]
                existing.label = row["label"]
                existing.field_type = row["field_type"]
                existing.display_order = row["display_order"]

        for row in TEMPLATE_FIELD_ROWS:
            existing = await session.get(
                ProposalTemplateFieldMap, (row["template_type"], row["field_key"])
            )
            if existing is None:
                session.add(ProposalTemplateFieldMap(**row))
            else:
                existing.requirement = row["requirement"]

        await session.commit()

        print(f"proposal_field_definitions   : {len(FIELD_DEFINITION_ROWS)}행")
        print(f"proposal_template_field_map  : {len(TEMPLATE_FIELD_ROWS)}행")


if __name__ == "__main__":
    asyncio.run(seed())
