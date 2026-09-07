"""제안서 자동 작성 API/LLM 테스트 (이슈 #102). DB/네트워크 불필요 -- 전부 mock.

field-definitions 실제 DB 조회 1건만 @pytest.mark.db로 표시한다
(`scripts/seed_proposal_fields.py` 실행 후 로컬에서 확인).
"""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.api import proposals
from app.api.proposals import (
    CompleteRequest,
    CompleteSection,
    _extract_pdf_text,
    _is_pdf,
    _placeholder_value,
    complete_proposal,
    get_field_definitions,
    get_proposal_pdf,
)
from app.domain import proposal_llm
from app.domain.proposal_llm import (
    ATTACHMENT_CHECKLISTS,
    TABLE_ITEM_SCHEMAS,
    ProposalLLMUnavailable,
    build_response_schema,
    generate_missing_sections,
)
from scripts.seed_proposal_fields import (
    FIELD_DEFINITION_ROWS,
    TEMPLATE_FIELD_ROWS,
    TEMPLATE_TYPES,
)


def _upload_file(filename: str, content_type: str) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(b"dummy"), headers=Headers({"content-type": content_type}))


def _fake_openai_response(content: str):
    message = MagicMock(content=content)
    choice = MagicMock(message=message)
    return MagicMock(choices=[choice])


def _patched_client(response_content: str):
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_fake_openai_response(response_content))
    return patch("app.domain.proposal_llm.AsyncOpenAI", return_value=mock_client)


# ---------------------------------------------------------------------------
# 필드 매트릭스 데이터 자체의 정합성 (DB 불필요 -- CI에서 실행)
# ---------------------------------------------------------------------------


def test_field_definition_keys_are_unique() -> None:
    keys = [row["field_key"] for row in FIELD_DEFINITION_ROWS]
    assert len(keys) == len(set(keys))


def test_field_types_are_known_values() -> None:
    allowed = {"TEXT", "CHECKLIST", "TABLE"}
    assert {row["field_type"] for row in FIELD_DEFINITION_ROWS} <= allowed


def test_every_field_has_a_description() -> None:
    # description은 app/domain/proposal_llm.py가 LLM 프롬프트에 그대로 넣는 값이라
    # 비어있으면 프롬프트 품질이 떨어진다.
    assert all(row["description"] for row in FIELD_DEFINITION_ROWS)


def test_attachment_checklist_is_checklist_type_not_text() -> None:
    # 리뷰 중 발견했던 모순(체크리스트라고 매트릭스에 적어놓고 API 예시는 텍스트로
    # 다뤘던 것)의 회귀 테스트.
    row = next(r for r in FIELD_DEFINITION_ROWS if r["field_key"] == "attachment_checklist")
    assert row["field_type"] == "CHECKLIST"


def test_table_fields_all_have_a_registered_item_schema() -> None:
    # 시딩 데이터(FIELD_DEFINITION_ROWS)와 LLM 스키마 목록(TABLE_ITEM_SCHEMAS)이
    # 서로 다른 파일에 있어 어긋날 수 있다 -- 여기서 교차 확인한다.
    table_field_keys = {row["field_key"] for row in FIELD_DEFINITION_ROWS if row["field_type"] == "TABLE"}
    assert table_field_keys == set(TABLE_ITEM_SCHEMAS.keys())


def test_attachment_checklists_cover_all_template_types() -> None:
    assert set(ATTACHMENT_CHECKLISTS.keys()) == set(TEMPLATE_TYPES)
    assert all(ATTACHMENT_CHECKLISTS[t] for t in TEMPLATE_TYPES)


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
# PDF 검증/추출 헬퍼, 자리표시자 (DB 불필요)
# ---------------------------------------------------------------------------


def test_is_pdf_accepts_pdf_extension_or_content_type() -> None:
    assert _is_pdf(_upload_file("report.pdf", "application/octet-stream"))
    assert _is_pdf(_upload_file("report", "application/pdf"))


def test_is_pdf_rejects_other_files() -> None:
    assert not _is_pdf(_upload_file("report.hwp", "application/x-hwp"))


def test_extract_pdf_text_is_callable() -> None:
    # 실제 PDF 바이트 케이스는 funding.py 쪽 test_funding_match.py가 이미 다룬다
    # (같은 pypdf 사용법 -- 여기서는 인터페이스만 회귀로 고정).
    assert callable(_extract_pdf_text)


def test_placeholder_value_is_empty_list_for_table_and_message_for_others() -> None:
    assert _placeholder_value("TABLE", "재무 추정") == []
    text = _placeholder_value("TEXT", "개발 배경·동기")
    assert "개발 배경·동기" in text


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
# app/domain/proposal_llm.py -- 전부 mock, DB/네트워크 불필요
# ---------------------------------------------------------------------------


def test_build_response_schema_maps_text_and_table_fields() -> None:
    schema = build_response_schema(
        [
            {"field_key": "background_motivation", "label": "개발 배경·동기", "field_type": "TEXT"},
            {"field_key": "growth_targets", "label": "정량적 성장목표", "field_type": "TABLE"},
        ]
    )
    props = schema["schema"]["properties"]
    assert props["background_motivation"] == {"type": "string"}
    assert props["growth_targets"]["type"] == "array"
    assert props["growth_targets"]["items"] == TABLE_ITEM_SCHEMAS["growth_targets"]
    assert schema["schema"]["required"] == ["background_motivation", "growth_targets"]


def test_build_response_schema_raises_for_unregistered_table_field() -> None:
    with pytest.raises(ValueError):
        build_response_schema([{"field_key": "does_not_exist", "label": "x", "field_type": "TABLE"}])


async def test_generate_missing_sections_returns_empty_dict_when_no_target_fields() -> None:
    # target_fields가 비면 OPENAI_API_KEY 여부와 무관하게 바로 반환돼야 한다.
    assert await generate_missing_sections("PSST", "report", {}, []) == {}


async def test_generate_missing_sections_raises_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(proposal_llm.settings, "openai_api_key", "")
    with pytest.raises(ProposalLLMUnavailable):
        await generate_missing_sections(
            "PSST", "report text", {}, [{"field_key": "background_motivation", "label": "x", "field_type": "TEXT"}]
        )


async def test_generate_missing_sections_parses_llm_response(monkeypatch) -> None:
    monkeypatch.setattr(proposal_llm.settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(proposal_llm.redis_client, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(proposal_llm.redis_client, "set", AsyncMock())

    payload = json.dumps({"background_motivation": "수면 문제는..."})
    with _patched_client(payload) as mock_openai_cls:
        result = await generate_missing_sections(
            "PSST",
            "report text",
            {},
            [{"field_key": "background_motivation", "label": "개발 배경·동기", "field_type": "TEXT"}],
        )
    mock_openai_cls.assert_called_once()
    assert result == {"background_motivation": "수면 문제는..."}


async def test_generate_missing_sections_raises_on_malformed_json(monkeypatch) -> None:
    monkeypatch.setattr(proposal_llm.settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(proposal_llm.redis_client, "get", AsyncMock(return_value=None))

    with _patched_client("이건 JSON이 아님"):
        with pytest.raises(ProposalLLMUnavailable):
            await generate_missing_sections(
                "PSST", "report", {}, [{"field_key": "background_motivation", "label": "x", "field_type": "TEXT"}]
            )


async def test_generate_missing_sections_uses_cache_on_second_call(monkeypatch) -> None:
    monkeypatch.setattr(proposal_llm.settings, "openai_api_key", "sk-test")
    store: dict[str, str] = {}

    async def fake_get(key: str):
        return store.get(key)

    async def fake_set(key: str, value: str, ex: int | None = None) -> None:
        store[key] = value

    monkeypatch.setattr(proposal_llm.redis_client, "get", fake_get)
    monkeypatch.setattr(proposal_llm.redis_client, "set", fake_set)

    target_fields = [{"field_key": "background_motivation", "label": "x", "field_type": "TEXT"}]
    payload = json.dumps({"background_motivation": "동일 결과"})

    with _patched_client(payload) as first_call:
        first = await generate_missing_sections("PSST", "report", {}, target_fields)
    first_call.assert_called_once()

    with _patched_client(payload) as second_call:
        second = await generate_missing_sections("PSST", "report", {}, target_fields)
    second_call.assert_not_called()  # 캐시 히트라 OpenAI를 다시 안 부른다.

    assert first == second


# ---------------------------------------------------------------------------
# complete / pdf -- 실제 Redis 대신 monkeypatch로 대체 (CI에서 실행)
# ---------------------------------------------------------------------------


async def test_complete_proposal_stores_payload_with_ttl(monkeypatch) -> None:
    fake_set = AsyncMock()
    monkeypatch.setattr(proposals.redis_client, "set", fake_set)

    request = CompleteRequest(sections=[CompleteSection(field_key="company_overview", value="최종본")])
    response = await complete_proposal("prop-1", request)

    assert response.result.proposal_id == "prop-1"
    fake_set.assert_awaited_once()
    call_args, kwargs = fake_set.call_args
    assert kwargs["ex"] == proposals._PROPOSAL_TTL_SECONDS
    assert call_args[0] == "proposal:prop-1"
    stored = json.loads(call_args[1])
    assert stored["sections"][0]["value"] == "최종본"


async def test_complete_proposal_accepts_checklist_and_table_values(monkeypatch) -> None:
    fake_set = AsyncMock()
    monkeypatch.setattr(proposals.redis_client, "set", fake_set)

    request = CompleteRequest(
        sections=[
            CompleteSection(field_key="attachment_checklist", value=["사업자등록증"]),
            CompleteSection(field_key="growth_targets", value=[{"year": 1, "revenue_krw": 0}]),
        ]
    )
    response = await complete_proposal("prop-2", request)
    assert response.result.proposal_id == "prop-2"


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
            "sections": [{"field_key": "company_overview", "value": "최종본"}],
            "expires_at": "2026-09-07T12:10:00+00:00",
        }
    )
    monkeypatch.setattr(proposals.redis_client, "get", AsyncMock(return_value=cached_payload))

    response = await get_proposal_pdf("prop-1")

    assert response.result.proposal_id == "prop-1"
    assert response.result.sections[0].value == "최종본"
