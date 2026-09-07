# 제안서 자동 작성 API 명세서

> 관련 이슈: #102
> `판정_API_명세서.md`/`시장성_BM_API_명세서.md`와 같은 포맷.
> DB 저장 없음(`db_구축_설계서.md` §1.3 "사용자 입력·분석결과 미저장" 원칙) — Redis TTL 캐시만 사용. `미결정_항목_정리.md` #1(E-4) "리포트 재조회·창업제안서 연계 방식 미정"을 본 문서로 확정한다.
>
> ⚠️ **리뷰 중 발견 (2026-09-07)**: `app/db/models/analysis_session.py`를 확인한 결과 `analysis_sessions`는 실제로 **Postgres에 영구 저장**되며, 삭제/TTL 로직이 코드에 없다(`analysis_sessions.py` API에 `DELETE` 엔드포인트 없음, cron/스케줄러 없음). 즉 §10.4 "사용자 입력·분석결과 미저장" 원칙이 검진 세션 자체에는 아직 구현돼 있지 않다 — 지금은 `session_id`만 있으면 검진 데이터가 계속 조회된다. 본 문서 §0/§5.2는 이 현재 상태를 전제로 작성했다. 검진 담당이 나중에 `analysis_sessions`에 실제 TTL 삭제를 붙이면, 아래 "검진 결과 직접 참조" 방식도 그 TTL 안에서만 유효해지므로 함께 조정 필요(§6-3 참고).

## 0. 전체 흐름

```
[아이디어 검진] 진행 → 검진 결과는 analysis_sessions(session_id)에 이미 저장돼 있음
        │
        ▼
[제안서 자동 작성] 탭에서 session_id 참조 + 지원사업 유형 선택
        │
        ▼
POST /proposals/generate  ── LLM이 유형별 필드 매트릭스 기준 초안 생성
        │
        ▼ (사용자가 화면에서 초안 검토/수정)
        │
"완료" 버튼 또는 "PDF 저장하기" 버튼
        │
        ▼
POST /proposals/{id}/complete  ── 이 시점부터 Redis TTL 10분 시작
        │
        ▼
GET /proposals/{id}/pdf  ── 10분 이내에만 다운로드 가능, 이후 자동 삭제
```

- 작성 중(완료 전) 상태는 **프론트 로컬 state로만 유지**한다. "임시저장" API는 없음.
- "완료"와 "PDF 저장하기"는 **동일한 트리거**로 취급한다 — 둘 중 어느 쪽을 먼저 눌러도 그 시점부터 10분 TTL이 시작된다. (프론트 확인 완료, 2026-09-07)
- 검진 결과는 **PDF 재업로드가 아니라 `session_id` 참조**로 가져온다 — `analysis_sessions`에 이미 구조화 저장돼 있어(위 발견 참고) PDF를 다시 파싱할 필요가 없다. 기존 "PDF 다운로드→재업로드" 아이디어는 이 발견 이후 폐기(§6-3).
- 제안서 자체는 검진 결과와 동일한 캐시 클라이언트/패턴 재사용: `app/core/redis_client.py`, `ex=` TTL 방식 (`trend_client.py`, `correction_llm.py` 참조).

## 1. 지원사업 유형 (template_type)

| 코드 | 명칭 | 비고 |
|---|---|---|
| `PSST` | 창업사업화 지원사업 (PSST 표준형) | 예비창업패키지·초기창업패키지·창업도약패키지 등. Problem-Solution-Scaleup-Team |
| `RND` | R&D 과제형 (기술개발사업) | 총괄연구개발계획·연구비 산정 등 PSST와 별도 양식 |
| `IR` | 투자유치용 (IR) | 민간 VC/엔젤 투자자 대상. TAM/SAM/SOM·재무추정·지분구조 포함 |

`category_1`(String(80) 자유 텍스트)과 동일한 이유로 `template_type`도 DB에서는 **닫힌 enum이 아니라 자유 텍스트**로 둔다 — 새 유형이 추가돼도 스키마 변경 없이 §3의 매핑 테이블에 행만 추가하면 된다.

## 2. 유형별 필드 매트릭스

범례: ● 필수 / ○ 선택 / − 제외

### 2.0 일반현황·개요
| field_key | 항목 | PSST | RND | IR |
|---|---|---|---|---|
| `company_overview` | 기업개요·대표자 | ● | ● | ● |
| `idea_overview` | 창업아이템 개요 | ● | ● | ● |
| `location_timing` | 창업예정지·시기 | ● | ○ | − |
| `project_period` | 사업 수행기간(총수행기간·협약기간) | ● | ● | ● |

### 2.1 문제인식
| field_key | 항목 | PSST | RND | IR |
|---|---|---|---|---|
| `background_motivation` | 개발 배경·동기 | ● | ● | ● |
| `target_market_analysis` | 목표시장 분석 | ● | ● | ● |

### 2.2 실현가능성
| field_key | 항목 | PSST | RND | IR |
|---|---|---|---|---|
| `dev_status` | 개발/사업화 현황 | ● | ● | ● |
| `feasibility_diff` | 실현방안·차별점 | ● | ● | ● |
| `ip_plan` | 지식재산권 확보 계획 | − | ○ | ○ |

### 2.3 성장전략
| field_key | 항목 | PSST | RND | IR |
|---|---|---|---|---|
| `funding_plan` | 자금조달 계획 | ● | ● | ● |
| `revenue_model` | 수익모델·시장진입 | ● | ● | ● |
| `schedule` | 사업 추진 일정 | ● | ● | ● |
| `growth_targets` | 정량적 성장목표(3개년 매출·고용 수치) | ● | ● | ● |
| `exit_strategy` | 출구(EXIT) 전략 | − | − | ○ |
| `overseas_expansion` | 해외시장 진출전략(타겟국가·GTM·진출실적) | ○ | − | ○ |

### 2.4 팀 구성
| field_key | 항목 | PSST | RND | IR |
|---|---|---|---|---|
| `founder_capability` | 대표자 역량 | ● | ● | ● |
| `team_hiring_plan` | 팀 구성·고용계획 [^1] | ● | ● | ● |
| `new_hire_plan` | 신규 인력 채용계획(고용창출 목표, 정량) | − | ● | ○ |
| `partnership` | 파트너십·외부협력 | − | ○ | ○ |

[^1]: PSST 유형에서는 `new_hire_plan`(신규 인력 채용계획)을 별도 필드로 분리하지 않고 `team_hiring_plan` 안에 포함해서 작성한다.

### 2.5 PREP 특화 항목
| field_key | 항목 | PSST | RND | IR |
|---|---|---|---|---|
| `regulatory_compliance` | 규제 준수 및 리스크 대응 | ● | ● | ○ |
| `data_strategy` | 데이터 확보 전략 | ● | ● | ○ |
| `general_risk_mgmt` | 일반 리스크 관리 계획(시장·운영 리스크) | ○ | ○ | ○ |
| `program_utilization` | 지원 프로그램 활용계획(참가목적 등) | ○ | ○ | ○ |

### 2.6 R&D 특화 항목
| field_key | 항목 | PSST | RND | IR |
|---|---|---|---|---|
| `rd_plan_budget` | 연구개발목표·연구비산정·참여연구원 | − | ● | − |
| `annual_budget_exec` | 연차별 사업비 집행계획(정부출연금/자기부담금 현금·현물 구분) | − | ● | − |
| `rd_track_record` | 정부지원 수혜실적 및 기존 R&D 이력 | − | ● | − |

### 2.7 투자유치용(IR) 추가 항목
| field_key | 항목 | PSST | RND | IR |
|---|---|---|---|---|
| `esg` | 사회적 가치·ESG | − | − | ○ |
| `bonus_criteria` | 우대 가점 사항 | − | ○ | ○ |
| `financial_projection` | 재무 추정(3~5개년, BEP) | − | − | ○ |
| `tam_sam_som` | TAM/SAM/SOM 시장규모 | − | − | ○ |
| `cap_table` | 지분구조(캡테이블) | − | − | ○ |

### 2.8 첨부서류 (텍스트 작성이 아닌 체크리스트 — §3의 field_type=CHECKLIST)
| field_key | 항목 | PSST | RND | IR |
|---|---|---|---|---|
| `attachment_checklist` | 첨부서류 체크리스트(사업자등록증·재무제표·납세증명서 등) | ● | ● | ● |

> `overseas_expansion`, `program_utilization`은 실제 지원사업 공고문 5건(인천공항공사 상생형·모두의창업·GX 오사카 Plug in·예비창업패키지·강북창업지원센터) 분석 과정에서 기존 매트릭스에 없던 항목으로 신규 확인되어 이번 작업에서 추가함 (근거는 이슈 #102 참고).

## 3. DB 스키마 (신규, 고정 참조 데이터 — `data_difficulty`/`collection_difficulty`와 동일한 "고정 기준표" 패턴)

리뷰 중 1차 초안의 `psst_requirement`/`rnd_requirement`/`ir_requirement` 3-컬럼 설계를 **폐기**했다 — 새 지원사업 유형이 추가될 때마다 컬럼을 늘려야 해서(ALTER TABLE) 교수님 피드백("표준 양식 하나로 고정하지 말고 확장 가능하게")과 정면으로 배치된다. `gate_matrix`처럼 **행 단위**로 바꿔 새 유형 추가 시 INSERT만으로 끝나게 한다.

### 3.1 `proposal_field_definitions` — 필드 자체의 정적 정보 (필드당 1행)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| field_key | VARCHAR, PK | 위 표의 field_key |
| category | VARCHAR | 일반현황 / 문제인식 / 실현가능성 / 성장전략 / 팀구성 / PREP특화 / RND특화 / IR추가 / 첨부서류 |
| label | VARCHAR | 화면 표시용 라벨 |
| description | TEXT | 작성 가이드 문구 (nullable) |
| field_type | VARCHAR | `TEXT`(서술형) / `CHECKLIST`(체크리스트) / `TABLE`(연도별 표 — 예: growth_targets, annual_budget_exec) |
| display_order | INTEGER | 화면 노출 순서 |

### 3.2 `proposal_template_field_map` — 유형×필드별 필수/선택 (유형-필드 쌍당 1행)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| template_type | VARCHAR | PSST / RND / IR (자유 텍스트, §1 참고) |
| field_key | VARCHAR, FK → proposal_field_definitions | |
| requirement | VARCHAR | REQUIRED / OPTIONAL (EXCLUDED는 행 자체를 안 만드는 것으로 표현 — 조회 시 없으면 제외) |

새 지원사업 유형이 추가되면 `proposal_template_field_map`에 행만 추가하면 되고, 겹치는 필드가 이미 있으면 `proposal_field_definitions`도 건드릴 필요 없다.

## 4. Headers

Authorization: Bearer `<accessToken>`

## 5. API 목록

### 5.1 `GET /api/v1/proposals/field-definitions?template_type={PSST|RND|IR}`

유형 선택 시 프론트가 동적으로 폼을 렌더링하기 위한 필드 목록 조회. `proposal_field_definitions` ⋈ `proposal_template_field_map`을 `template_type`으로 조회 — 매핑 행이 없는 필드(=EXCLUDED)는 응답에서 자연히 빠진다.

```json
{
  "isSuccess": true,
  "code": "COMMON200",
  "message": "성공",
  "result": {
    "template_type": "PSST",
    "fields": [
      { "field_key": "company_overview", "category": "일반현황", "label": "기업개요·대표자", "field_type": "TEXT", "requirement": "REQUIRED", "display_order": 1 },
      { "field_key": "attachment_checklist", "category": "첨부서류", "label": "첨부서류 체크리스트", "field_type": "CHECKLIST", "requirement": "REQUIRED", "display_order": 40 },
      { "field_key": "overseas_expansion", "category": "성장전략", "label": "해외시장 진출전략", "field_type": "TEXT", "requirement": "OPTIONAL", "display_order": 22 }
    ]
  }
}
```

### 5.2 `POST /api/v1/proposals/generate`

검진 세션(`session_id`, `analysis_sessions` 참조) + 선택 유형 + 사용자가 채운 필드값을 받아 LLM이 제안서 초안을 생성한다. 이 시점에는 아직 완료 전이므로 **응답은 캐시에 저장하지 않는다** — 재요청 시 매번 새로 생성.

```json
// 요청
{
  "session_id": "string",             // analysis_sessions.session_id — 검진 결과 직접 참조
  "template_type": "PSST",
  "field_values": {
    "company_overview": "string",
    "attachment_checklist": ["사업자등록증", "재무제표"],
    "overseas_expansion": "string"
  }
}
```

`field_values`의 값 타입은 §3.1 `field_type`을 따른다 — `TEXT`는 문자열, `CHECKLIST`는 문자열 배열, `TABLE`은 `[{"year": 1, "revenue": 0, "headcount": 0}, ...]` 형태의 배열.

```json
// 응답
{
  "isSuccess": true,
  "code": "COMMON200",
  "message": "성공",
  "result": {
    "proposal_id": "string",
    "template_type": "PSST",
    "sections": [
      { "field_key": "company_overview", "label": "기업개요·대표자", "generated_text": "string" }
    ]
  }
}
```

### 5.3 `POST /api/v1/proposals/{proposal_id}/complete`

"완료" 또는 "PDF 저장하기" 클릭 시 호출. 사용자가 수정한 최종본을 받아 Redis에 저장하고 10분 TTL을 시작한다.

```json
// 요청
{ "sections": [ { "field_key": "company_overview", "final_text": "string" } ] }
```

```json
// 응답
{
  "isSuccess": true,
  "code": "COMMON200",
  "message": "성공",
  "result": { "proposal_id": "string", "expires_at": "2026-09-07T12:10:00+09:00" }
}
```

### 5.4 `GET /api/v1/proposals/{proposal_id}/pdf`

10분 이내에만 다운로드 가능. `complete` 호출 전이면 404.

```json
// 만료/미완료 시 에러 응답 (404)
{
  "isSuccess": false,
  "code": "PROPOSAL_NOT_FOUND",
  "message": "제안서를 찾을 수 없거나 만료되었습니다.",
  "result": null
}
```

## 6. 후속 논의 필요

| # | 항목 |
|---|---|
| 1 | PDF 생성을 동기(요청-응답)로 할지, presigned URL 발급 방식으로 할지 |
| 2 | `generate` 응답 이후 사용자가 재생성을 요청할 수 있는 횟수 제한 여부 |
| 3 | **(리뷰 중 갱신)** `session_id` 직접 참조가 지금은 기술적으로 가능하지만(analysis_sessions가 영구 저장 중), 검진 담당이 §10.4 원칙대로 TTL 삭제를 나중에 붙이면 "검진 후 며칠 뒤에 제안서 작성" 같은 흐름은 막힌다. 검진 세션 TTL을 도입할 계획이 있는지, 있다면 몇 분/시간으로 할지 검진 담당과 맞춰야 한다 |
