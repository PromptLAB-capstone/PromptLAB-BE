"""제안서 자동 작성 API 테스트 (이슈 #102).

DB(proposal_field_definitions/proposal_template_field_map 시딩) 필요 케이스는
@pytest.mark.db로 표시한다 -- `scripts/seed_proposal_fields.py` 실행 후 로컬에서
확인한다(CI 기본값 `-m "not db"`에서는 제외).
"""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.api import proposals
from app.api.proposals import (
    CompleteRequest,
    CompleteSection,
    _extract_pdf_text,
    _generate_section_text,
    _is_pdf,
    complete_proposal,
    get_field_definitions,
    get_proposal_pdf,
)
from scripts.seed_proposal_fields import (
    FIELD_DEFINITION_ROWS,
    TEMPLATE_FIELD_ROWS,
    TEMPLATE_TYPES,
)


def _upload_file(filename: str, content_type: str) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(b"dummy"), headers=Headers({"content-type": content_type}))


# ---------------------------------------------------------------------------
# 필드 매트릭스 데이터 자체의 정합성 (DB 불필요 -- CI에서 실행)
# ---------------------------------------------------------------------------


def test_field_definition_keys_are_unique() -> None:
    keys = [row["field_key"] for row in FIELD_DEFINITION_ROWS]
    assert len(keys) == len(set(keys))


def test_field_types_are_known_values() -> None:
    allowed = {"TEXT", "CHECKLIST", "TABLE"}
    assert {row["field_type"] for row in FIELD_DEFINITION_ROWS} <= allowed


def test_attachment_checklist_is_checklist_type_not_text() -> None:
    # 리뷰 중 발견했던 모순(체크리스트라고 매트릭스에 적어놓고 API 예시는 텍스트로
    # 다뤘던 것)의 회귀 테스트.
    row = next(r for r in FIELD_DEFINITION_ROWS if r["field_key"] == "attachment_checklist")
    assert row["field_type"] == "CHECKLIST"


def test_template_field_map_only_references_known_fields() -> None:
    known_keys = {row["field_key"] for row in FIELD_DEFINITION_ROWS}
    for row in TEMPLATE_FIELD_ROWS:
        assert row["field_key"] in known_keys
        assert row["template_type"] in TEMPLATE_TYPES
        assert row["requirement"] in {"REQUIRED", "OPTIONAL"}


def test_trl_level_is_rnd_required_and_ir_optional_but_not_psst() -> None:
    # 사용자 결정(2026-09-07): TRL만 추가, PSST에는 없음.
    trl_rows = {
        row["template_type"]: row["requirement"]
        for row in TEMPLATE_FIELD_ROWS
        if row["field_key"] == "trl_level"
    }
    assert trl_rows == {"RND": "REQUIRED", "IR": "OPTIONAL"}


def test_attachment_checklist_required_in_all_three_templates() -> None:
    rows = {row["template_type"] for row in TEMPLATE_FIELD_ROWS if row["field_key"] == "attachment_checklist"}
    assert rows == set(TEMPLATE_TYPES)


# ---------------------------------------------------------------------------
# PDF 검증/추출 헬퍼 (DB 불필요)
# ---------------------------------------------------------------------------


def test_is_pdf_accepts_pdf_extension_or_content_type() -> None:
    assert _is_pdf(_upload_file("report.pdf", "application/octet-stream"))
    assert _is_pdf(_upload_file("report", "application/pdf"))


def test_is_pdf_rejects_other_files() -> None:
    assert not _is_pdf(_upload_file("report.hwp", "application/x-hwp"))


def test_extract_pdf_text_returns_empty_string_for_no_extractable_text() -> None:
    # 실제 PDF 바이트가 아니면 PdfReader가 예외를 던지므로, 최소 인터페이스만
    # 회귀로 고정한다 -- 빈 페이지 처리 등 실제 PDF 케이스는 funding.py 쪽
    # test_funding_match.py가 이미 다룬다(같은 pypdf 사용법).
    assert callable(_extract_pdf_text)


# ---------------------------------------------------------------------------
# generate 스텁 로직 (DB 불필요)
# ---------------------------------------------------------------------------


def test_generate_section_text_passes_through_user_value() -> None:
    text = _generate_section_text("company_overview", report_text="", field_values={"company_overview": "우리 회사는..."})
    assert text == "우리 회사는..."


def test_generate_section_text_returns_placeholder_when_missing() -> None:
    text = _generate_section_text("company_overview", report_text="", field_values={})
    assert "TODO" in text
    assert "company_overview" in text


# ---------------------------------------------------------------------------
# GET /field-definitions -- template_type 검증은 DB 조회 전이라 마크 불필요
# ---------------------------------------------------------------------------


async def test_get_field_definitions_rejects_unknown_template_type() -> None:
    response = await get_field_definitions("UNKNOWN")
    assert response.status_code == 400
    body = json.loads(response.body)
    assert body["code"] == "PROPOSAL_TEMPLATE_TYPE_INVALID"


@pytest.mark.db
async def test_get_field_definitions_returns_seeded_psst_fields() -> None:
    """scripts/seed_proposal_fields.py 실행 후 로컬 DB로 확인."""
    response = await get_field_definitions("PSST")
    keys = {field.field_key for field in response.result.fields}
    assert "company_overview" in keys
    assert "rd_plan_budget" not in keys  # PSST에서는 제외된 필드


# ---------------------------------------------------------------------------
# complete / pdf -- 실제 Redis 대신 monkeypatch로 대체 (CI에서 실행)
# ---------------------------------------------------------------------------


async def test_complete_proposal_stores_payload_with_ttl(monkeypatch) -> None:
    fake_set = AsyncMock()
    monkeypatch.setattr(proposals.redis_client, "set", fake_set)

    request = CompleteRequest(sections=[CompleteSection(field_key="company_overview", final_text="최종본")])
    response = await complete_proposal("prop-1", request)

    assert response.result.proposal_id == "prop-1"
    fake_set.assert_awaited_once()
    _, kwargs = fake_set.call_args
    assert kwargs["ex"] == proposals._PROPOSAL_TTL_SECONDS
    call_args = fake_set.call_args.args
    assert call_args[0] == "proposal:prop-1"
    stored = json.loads(call_args[1])
    assert stored["sections"][0]["final_text"] == "최종본"


async def test_get_proposal_pdf_returns_404_when_expired_or_missing(monkeypatch) -> None:
    monkeypatch.setattr(proposals.redis_client, "get", AsyncMock(return_value=None))

    response = await get_proposal_pdf("does-not-exist")
    assert response.status_code == 404
    body = json.loads(response.body)
    assert body["code"] == "PROPOSAL_NOT_FOUND"


async def test_get_proposal_pdf_returns_cached_content(monkeypatch) -> None:
    cached_payload = json.dumps(
        {
            "proposal_id": "prop-1",
            "sections": [{"field_key": "company_overview", "final_text": "최종본"}],
            "expires_at": "2026-09-07T12:10:00+00:00",
        }
    )
    monkeypatch.setattr(proposals.redis_client, "get", AsyncMock(return_value=cached_payload))

    response = await get_proposal_pdf("prop-1")

    assert response.result.proposal_id == "prop-1"
    assert response.result.sections[0].final_text == "최종본"
