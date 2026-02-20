# Bloom - Webview 급전지시 모니터링 초기 세팅

사내망 VPN 환경에서만 접근 가능한 `Webview` 데이터를 수집하고,
`[급전지시]` 이벤트 발생 시점의 발전량을 기록/조회하기 위한 초기 개발 템플릿입니다.

## 목표
- VPN 연결 상태에서만 동작하는 크롤러 실행
- 급전지시 이벤트 + 발전량 시계열 저장
- 웹 대시보드에서 상태를 한눈에 확인

## 권장 아키텍처 (v0)
1. **수집기(Crawler)**: Playwright 기반 로그인/조회
2. **API 서버**: FastAPI (이벤트/발전량 조회, 수동 수집 트리거)
3. **DB**: PostgreSQL (이벤트, 발전량, 수집 로그)
4. **스케줄러**: APScheduler 또는 Celery beat(후속)

## 빠른 시작
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
cp .env.example .env
uvicorn bloom.main:app --reload
```

실행 후 아래 경로를 확인할 수 있습니다.
- `http://127.0.0.1:8000/dashboard` : 운영 Summary 메인(Live API 기본)
- `http://127.0.0.1:8000/summary` : `/dashboard` alias
- `http://127.0.0.1:8000/sites/SKK046?date=YYYY-MM-DD` : 개별 현장 상세
- `http://127.0.0.1:8000/site/SKK046?date=YYYY-MM-DD` : 개별 현장 상세(legacy alias)
- `http://127.0.0.1:8000/ui-kit` : 개발용 Summary preview(기본 normal)
- `http://127.0.0.1:8000/ui-kit?scenario=loading|empty|normal|activeHighCapacity` : 상태별 미리보기

`/ui-kit`은 `src/bloom/ui_fixtures/*.json` fixture만 사용하므로 DB/실데이터 없이 항상 렌더링됩니다. `/dashboard`는 운영용 Summary(Live API 기본) 화면입니다.

## 서버 데이터 업데이트 주기 권장안
- 기본(상시 모니터링): **60초**
- 급전지시 진행 시간대(집중 모니터링): **10~30초**
- 비상/시운전(짧은 기간): **5~10초** (서버 부하/차단 정책 확인 후 한시 적용)

### 왜 이렇게 권장하나?
- 너무 짧으면(Webview 요청 과다) 로그인 세션 만료/차단/부하 위험이 커집니다.
- 너무 길면(예: 2~5분) 급전지시 도달/이탈 시점을 늦게 감지합니다.
- 따라서 운영은 **기본 60초 + 이벤트 시간대 단축(10~30초)**의 하이브리드가 가장 현실적입니다.

### 현재 코드 기준
- 환경변수 `crawl_interval_seconds`로 제어하며 기본값은 `60`입니다.
- 추후 스케줄러 연결 시, 시간대별로 간격을 자동 전환하도록 확장하는 것을 권장합니다.

## 초기 구현 순서 (추천)
1. **VPN + 인증 검증**: Playwright로 로그인 성공 여부 확인
2. **급전지시 식별 규칙 확정**: 텍스트/상태코드/DOM 위치
3. **발전량 파서 작성**: 단위(MW/kW), 타임존, 소수점 처리
4. **DB 스키마 고정**: 이벤트 중복키(발생시각+발전소+타입)
5. **대시보드 MVP**: 최근 이벤트, 현재 발전량, 누락/실패 알림
6. **현장 활성화 플로우**: site ID 선택(+), 제출/감발(min)/복원(max) 입력
7. **프로그램 시작 시초기록**: 시작 버튼으로 open output 스냅샷 고정

## 문서
- 요구사항 질문지: `docs/discovery-questions.md`
- 아키텍처/기술선정 가이드: `docs/architecture-decision.md`
- 로직 명세 템플릿(주식형 UI 매핑): `docs/dispatch-logic-spec.md`
- VPN 불가 환경 대응 승인 아키텍처: `docs/vpn-approval-architecture.md`
- VPN 전략 의사결정 가이드: `docs/vpn-strategy-decision.md`
- 사용자 구동 흐름(하이브리드 운영): `docs/user-operation-flow.md`
- 2대 PC 설치/시운전 런북: `docs/two-pc-install-runbook.md` ("어디서, 어떻게 확인" 빠른 확인표 포함)
- 서버/사용자 PC 구동 모습 가이드: `docs/server-vs-user-runtime.md`
- 운영 전 빈부분 체크리스트: `docs/production-gap-checklist.md`


## PR 단위 실행/검증 메모
- **PR0 (문서만)**
  - `docs/ui/SUMMARY_PAGE_SPEC.md`, `docs/api/API_CONTRACT.md` 확인
- **PR1 (mock 미리보기)**
  - 서버 실행 후 `http://127.0.0.1:8000/ui-kit` 접속
  - `?scenario=loading|empty|normal|activeHighCapacity` 확인
- **PR2 (차트/필터)**
  - X축 09:00~17:00 고정, 1h 라벨/10min 그리드 확인
  - Y축 max가 active capacity 만단위 올림인지 확인
  - 툴팁 2줄(`HH:mm`, `siteId · kW (tmo%)`) 확인
  - 그룹/사이트 체크박스 tri-state 동작 확인
- **PR3 (테이블 인라인 편집 + role 제한)**
  - role=viewer/supporter에서 편집 read-only 확인
  - role=operator에서 Enter 입력 시 `Saving…` -> `Saved ✓`(약 1~1.5초) + 셀 하이라이트 확인
  - 시스템 로그 포맷 `[HH:mm:ss] {siteId} {field} : {old} → {new}` 확인
- **PR4 (API)**
  - `GET /api/meta`, `GET /api/summary` 확인
  - `/ui-kit`에서 Data Source를 live로 전환 후 date/reload/export 동작 확인
  - `PATCH /api/schedule`와 `GET /api/export.xlsx`는 `X-User-Role: operator`에서만 성공 확인


## 운영 점검 URL
- `/health`
- `/api/version` (현재 서버가 summary/site-detail 라우트를 포함한 빌드인지 확인)
- `/api/routes` (실행 중 서버가 가진 실제 라우트 목록 확인)

PowerShell에서 빠르게 확인:
```powershell
(Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing).Content
```
응답의 `mainModulePath`가 실제 실행하려는 프로젝트 경로(예: `C:\Users\...\bloom\src\bloom\main.py`)인지 확인하세요.
또한 `hasSummaryRoute=true`, `hasSiteDetailRoute=true`인지 함께 확인하세요.
- `/dashboard`
- `/api/meta`
- `/api/summary?date=YYYY-MM-DD`
- `/api/export.xlsx?date=YYYY-MM-DD` (operator only)
- `/api/history?siteId=SKK046&from=2026-01-01`
- `/api/history/summary?siteId=SKK046&from=2026-01-01`

## Role 설정
- 상단 Role selector로 `viewer|supporter|operator`를 선택하면 localStorage에 저장됩니다.
- `viewer/supporter`는 read-only, `operator`만 Enter autosave 및 export 가능.
