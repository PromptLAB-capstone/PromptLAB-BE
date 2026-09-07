from datetime import date

from app.domain.funding_match import (
    FundingProgram,
    extract_funding_profile,
    score_funding_program,
    sort_funding_matches,
)


def test_extract_funding_profile_handles_spaced_korean_pdf_text() -> None:
    text = """
    PREP 리포트
    슬 립
    사용자의 수면 패턴을 분석하고 맞춤형 수면 루틴을 추천하는 모바일 앱입니다.
    # 수 면 # 데 이 터 기 록 관 리 # 수 면 관 심 층, 30대, 직장인 # 모 바 일 앱
    """

    profile = extract_funding_profile(text, region="충남", startup_stage="예비창업", keywords="AI, 모바일")

    assert profile.category_1 == "수면"
    assert profile.category_2 == "데이터 기록관리"
    assert profile.service_type == "모바일 앱"
    assert profile.region == "충남"
    assert profile.startup_stage == "예비창업"
    assert "수면 관심층" in profile.targets
    assert "AI" in profile.keywords


def test_score_funding_program_uses_keywords_region_stage_and_deadline() -> None:
    profile = extract_funding_profile(
        "수면 데이터를 기록 분석하는 모바일 앱 # 수면 # 데이터 기록관리 # 모바일 앱",
        region="충남",
        startup_stage="예비창업",
        keywords="AI",
    )
    program = FundingProgram(
        program_id="fund-test-1",
        title="충남 AI 헬스케어 예비창업 지원사업",
        region="충남",
        stage="예비창업",
        deadline=date(2026, 9, 10),
        max_amount=50000000,
        description="수면, 모바일 앱, 데이터 기록관리 서비스 개발비를 지원합니다.",
        keywords=["AI", "헬스케어", "수면"],
    )

    match = score_funding_program(program, profile, date(2026, 9, 7))

    assert match.match_score >= 80
    assert match.days_left == 3
    assert any("서비스 분야" in reason for reason in match.matched_reasons)
    assert any("지역 조건" in reason for reason in match.matched_reasons)


def test_sort_funding_matches_uses_score_deadline_then_amount() -> None:
    today = date(2026, 9, 7)
    profile = extract_funding_profile("AI 헬스케어 앱", keywords="AI")
    first = FundingProgram(
        program_id="first",
        title="마감 가까운 사업",
        deadline=date(2026, 9, 8),
        max_amount=10000000,
        description="AI 지원",
        keywords=["AI"],
    )
    second = FundingProgram(
        program_id="second",
        title="금액 큰 사업",
        deadline=date(2026, 9, 20),
        max_amount=90000000,
        description="AI 지원",
        keywords=["AI"],
    )
    third = FundingProgram(
        program_id="third",
        title="점수 높은 사업",
        deadline=date(2026, 9, 30),
        max_amount=1000000,
        description="AI 헬스케어 앱 서비스",
        keywords=["AI", "헬스케어", "앱"],
    )

    matches = [
        score_funding_program(first, profile, today),
        score_funding_program(second, profile, today),
        score_funding_program(third, profile, today),
    ]
    sorted_ids = [match.program.program_id for match in sort_funding_matches(matches)]

    assert sorted_ids[0] == "third"
    assert sorted_ids[1:] == ["first", "second"]
