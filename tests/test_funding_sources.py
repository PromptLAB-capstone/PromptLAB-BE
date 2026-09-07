from datetime import date

from app.domain.funding_sources import _find_items, _normalize_program, _parse_date


def test_find_items_handles_public_data_nested_payload() -> None:
    payload = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {
                            "biz_pbanc_sn": "123",
                            "biz_pbanc_nm": "AI 창업 지원사업",
                        }
                    ]
                }
            }
        }
    }

    assert _find_items(payload) == [{"biz_pbanc_sn": "123", "biz_pbanc_nm": "AI 창업 지원사업"}]


def test_normalize_program_maps_kstartup_like_fields() -> None:
    program = _normalize_program(
        {
            "biz_pbanc_sn": "123",
            "biz_pbanc_nm": "충남 AI 헬스케어 예비창업 지원사업",
            "detl_pg_url": "https://www.k-startup.go.kr/example",
            "biz_rcept_end_dt": "20260916",
            "supt_regin": "충남",
            "aply_trgt_ctnt": "예비창업자",
            "biz_pbanc_ctnt": "AI 헬스케어 모바일 앱 개발비를 최대 5천만원 지원합니다.",
        },
        source="K-Startup",
    )

    assert program is not None
    assert program.program_id == "123"
    assert program.title == "충남 AI 헬스케어 예비창업 지원사업"
    assert program.deadline == date(2026, 9, 16)
    assert program.region == "충남"
    assert program.max_amount == 50000000
    assert "AI" in program.keywords


def test_parse_date_handles_deadline_label() -> None:
    assert _parse_date("2026.09.16") == date(2026, 9, 16)
